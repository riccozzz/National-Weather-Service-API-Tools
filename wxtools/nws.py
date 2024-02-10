"""
High level objects for data from the National Weather Service.
"""
from __future__ import annotations
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, tzinfo
from typing import Any, Optional, Union

import pytz
from shapely import wkt
from shapely.geometry import Point

from .errors import NwsDataError
from .nwsapi import points, station_observations_latest, stations_id
from .units import UnitInfo, convert, unit_by_label, unit_by_namespace


class MadisQualityControl:
    """
    For values in observation records, the quality control flag from the MADIS
    system. See below for additional information.

    No QC available:
    * 'Z' -- Preliminary, no QC

    Automated QC checks:
    * 'C' -- Coarse pass, passed level 1.
    * 'S' -- Screened, passed levels 1 and 2.
    * 'V' -- Verified, passed levels 1, 2, and 3.
    * 'X' -- Rejected/erroneous, failed level 1.
    * 'Q' -- Questioned, passed level 1, failed 2 or 3.

    Where levels are:
    * level 1: Validity.
    * level 2: Internal consistency, temporal consistency, statistical spatial
    consistency checks.
    * level 3: Spatial consistency check.

    Subjective intervention:
    * 'G' -- Subjective good.
    * 'B' -- Subjective bad.

    Interpolated/Corrected observations:
    * 'T' -- Virtual temperature could not be calculated, air temperature passing
    all QC checks has been returned.

    The definitions of these flags can be found at
    https://madis.ncep.noaa.gov/madis_sfc_qc_notes.shtml
    """

    _quality_control: dict[str, str] = {
        "Z": "Preliminary, no QC",
        "C": "Coarse pass, passed level 1",
        "S": "Screened, passed levels 1 and 2",
        "V": "Verified, passed levels 1, 2, and 3",
        "X": "Rejected/erroneous, failed level 1",
        "Q": "Questioned, passed level 1, failed 2 or 3",
        "G": "Subjective good",
        "B": "Subjective bad",
        "T": (
            "Virtual temperature could not be calculated, air temperature"
            " passing all QC checks has been returned"
        ),
    }

    def __init__(self, flag: str) -> None:
        """
        Creates a MadisQualityControl object with the given flag. Raises
        KeyError if the flag is not known.

        Parameters:
        * flag (str) -- The single character MADIS quality control flag.
        """
        self._description = self._quality_control[flag]
        self._flag = flag

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(flag='{self._flag}"
            f"', description='{self._description}')"
        )

    def __str__(self) -> str:
        return f"{self._description} (flag='{self._flag}')"

    @property
    def flag(self) -> str:
        """The single character quality control flag."""
        return self._flag

    @property
    def description(self) -> str:
        """Descriptive definition of the quality control flag."""
        return self._description


class Measurement:
    """
    A structured floating point value representing a measurement and its unit of
    measure, loosely based on the schema.org definition:
    https://schema.org/QuantitativeValue
    """

    def __init__(
        self,
        value: Any,
        unit: UnitInfo,
        min_value: Optional[Any] = None,
        max_value: Optional[Any] = None,
        quality_control: Optional[MadisQualityControl] = None,
    ) -> None:
        """
        Raises:
        * ValueError -- Value is not convertable to a float.
        """
        if value is None:
            self._value = None
        elif isinstance(value, float):
            self._value = value
        else:
            self._value = float(value)

        self._unit = unit

        if min_value is None:
            self._min_value = None
        elif isinstance(min_value, float):
            self._min_value = min_value
        else:
            self._min_value = float(min_value)

        if max_value is None:
            self._max_value = None
        elif isinstance(max_value, float):
            self._max_value = max_value
        else:
            self._max_value = float(max_value)

        self._quality_control = quality_control

    def __repr__(self) -> str:
        sb = f"{self.__class__.__name__}("
        sb = f"{sb}value={self._value}, "
        sb = f"{sb}unit='{self._unit}', "
        if self._min_value is not None:
            sb = f"{sb}min_value={self._min_value}, "
        if self._max_value is not None:
            sb = f"{sb}max_value={self._max_value}, "
        if self._quality_control is not None:
            sb = f"{sb}quality_control='{self._quality_control.flag}', "
        return f"{sb[:-2]})"

    def __str__(self) -> str:
        if self._value is None:
            return "None"
        sb = f"{self._value:.1f} {self._unit.symbol}"
        if self._min_value is not None and self._max_value is None:
            sb = f"{sb} (min={self._min_value:.1f})"
        elif self._max_value is not None and self._min_value is None:
            sb = f"{sb} (max={self._max_value:.1f})"
        elif self._max_value is not None and self._min_value is not None:
            sb = f"{sb} (min={self._min_value:.1f}, max={self._max_value:.1f})"
        return sb

    @classmethod
    def from_json(cls, jdata: dict[str, Any]) -> Measurement:
        """

        Raises:
        * KeyError -- If a required json key does not exist.
        """
        value = jdata["value"]
        unit_code = jdata["unitCode"]
        if not isinstance(unit_code, str):
            raise NwsDataError(f"Invalid or unknown unit code: {unit_code}")
        unit = unit_by_namespace(unit_code)
        min_value = jdata.get("minValue")
        max_value = jdata.get("maxValue")
        qc = jdata.get("qualityControl")
        if isinstance(qc, str):
            qc = MadisQualityControl(qc)
        else:
            qc = None
        return cls(
            value=value,
            unit=unit,
            min_value=min_value,
            max_value=max_value,
            quality_control=qc,
        )

    def as_unit(self, to_unit: UnitInfo) -> Measurement:
        """
        Returns a new instance of this measurement with the specified unit.
        """
        if to_unit == self._unit:
            return self
        if self._value is not None:
            conv_value = convert(self._value, self._unit, to_unit)
        else:
            conv_value = None
        if self._min_value is not None:
            conv_min = convert(self._min_value, self._unit, to_unit)
        else:
            conv_min = None
        if self._max_value is not None:
            conv_max = convert(self._max_value, self._unit, to_unit)
        else:
            conv_max = None
        return Measurement(
            value=conv_value,
            unit=to_unit,
            min_value=conv_min,
            max_value=conv_max,
            quality_control=self._quality_control,
        )

    # Read only properties
    @property
    def value(self) -> Optional[float]:
        """The floating point value of the measurement."""
        return self._value

    @property
    def min_value(self) -> Optional[float]:
        """The optional floating point value of the minimum measurement."""
        return self._min_value

    @property
    def max_value(self) -> Optional[float]:
        """The optional floating point value of the maximum measurement."""
        return self._max_value

    @property
    def quality_control(self) -> Optional[MadisQualityControl]:
        """The MADIS quality control for this measurement, if available."""
        return self._quality_control

    # Read/write properties
    @property
    def unit(self) -> UnitInfo:
        """The floating point value of the measurement."""
        return self._unit

    @unit.setter
    def unit(self, to_unit: UnitInfo) -> None:
        """Converts all values in the object to the specified unit."""
        return self.convert_to(to_unit)

    def convert_to(self, to_unit: UnitInfo) -> None:
        """
        Converts a floating point value from one unit to another. The two units
        must be of the same kind (ie both 'temperature' or 'length'). If min or
        max values exist, they will also be converted.

        This method is equivalent to setting the unit property to a new unit,
        and will simply convert the units of measurement inplace.

        Raises:
        * ConversionError -- If the units are incompatible.
        """
        if to_unit == self._unit:
            return
        if self._value is not None:
            self._value = convert(self._value, self._unit, to_unit)
        if self._min_value is not None:
            self._min_value = convert(self._min_value, self._unit, to_unit)
        if self._max_value is not None:
            self._max_value = convert(self._max_value, self._unit, to_unit)
        self._unit = to_unit


def _get_measurement(
    nws_json_data: dict[str, Any], key: str, unit: Optional[UnitInfo] = None
) -> Measurement:
    value = nws_json_data[key]
    if isinstance(value, dict):
        measurement = Measurement.from_json(value)
        if unit is not None:
            measurement.unit = unit
        return measurement
    raise NwsDataError(
        f"Invalid measurement type for key '{key}'. Expecting a "
        f"QuantitativeValue (dict[str, Any]) but got type '{type(value)}'."
    )


@dataclass
class Temperature:
    """Dataclass for grouping of various temperature observations."""

    # TODO
    # Add calculations for derived values such as heat index and wind chill if
    # they are not provided, as an option.

    temperature: Measurement
    dew_point: Measurement
    relative_humidity: Measurement
    heat_index: Measurement
    wind_chill: Measurement
    min_last_24h: Measurement
    max_last_24h: Measurement

    def __str__(self) -> str:
        if self.temperature.value is None:
            return "Temperature not available"
        if self.temperature.unit.label == "fahrenheit":
            convert_unit = unit_by_label("celsius")
        else:
            convert_unit = unit_by_label("fahrenheit")
        sb = f"{self.temperature} ({self.temperature.as_unit(convert_unit)})"
        if self.dew_point.value is not None:
            sb = (
                f"{sb}, Dew Point {self.dew_point} "
                f"({self.dew_point.as_unit(convert_unit)})"
            )
            if self.relative_humidity.value is not None:
                sb = f"{sb}, Humidity {self.relative_humidity}"
        if self.heat_index.value is not None:
            sb = (
                f"{sb}, Feels Like {self.heat_index} "
                f"({self.heat_index.as_unit(convert_unit)})"
            )
        elif self.wind_chill.value is not None:
            sb = (
                f"{sb}, Feels Like {self.wind_chill} "
                f"({self.wind_chill.as_unit(convert_unit)})"
            )
        return sb

    @classmethod
    def from_json(
        cls, nws_json_data: dict[str, Any], unit: Optional[UnitInfo] = None
    ) -> Temperature:
        """
        Creates object from JSON data recieved from an NWS Observation.
        """
        temperature = _get_measurement(nws_json_data, "temperature", unit)
        dew_point = _get_measurement(nws_json_data, "dewpoint", unit)
        rh = _get_measurement(nws_json_data, "relativeHumidity")
        heat_index = _get_measurement(nws_json_data, "heatIndex", unit)
        wind_chill = _get_measurement(nws_json_data, "windChill", unit)
        mn = _get_measurement(nws_json_data, "minTemperatureLast24Hours", unit)
        mx = _get_measurement(nws_json_data, "maxTemperatureLast24Hours", unit)
        return cls(
            temperature=temperature,
            dew_point=dew_point,
            relative_humidity=rh,
            heat_index=heat_index,
            wind_chill=wind_chill,
            min_last_24h=mn,
            max_last_24h=mx,
        )


@dataclass
class Precipitation:
    """Dataclass for grouping of precipitation in weather observations."""

    last_hour: Measurement
    last_3_hours: Measurement
    last_6_hours: Measurement

    def __str__(self) -> str:
        if self._no_precip():
            return "No precipitation recorded in the past 6 hours."
        return (
            f"Last Hour: {self.last_hour}"
            f", 3 Hours: {self.last_3_hours}"
            f", 6 Hours: {self.last_6_hours}"
        )

    def _no_precip(self) -> bool:
        if (
            self.last_hour.value is None
            and self.last_3_hours.value is None
            and self.last_6_hours.value is None
        ):
            return True
        return False

    @classmethod
    def from_json(
        cls, nws_json_data: dict[str, Any], unit: Optional[UnitInfo] = None
    ) -> Optional[Precipitation]:
        """
        Creates object from JSON data recieved from an NWS Observation.

        Note that this is an all or nothing construction to align with NWS data.
        """
        try:
            return cls(
                last_hour=_get_measurement(
                    nws_json_data, "precipitationLastHour", unit
                ),
                last_3_hours=_get_measurement(
                    nws_json_data, "precipitationLast3Hours", unit
                ),
                last_6_hours=_get_measurement(
                    nws_json_data, "precipitationLast6Hours", unit
                ),
            )
        except KeyError:
            return None


@dataclass
class Pressure:
    """Dataclass for grouping of various pressure observations."""

    station_pressure: Measurement
    mslp: Measurement

    def __str__(self) -> str:
        if self.station_pressure.value is None and self.mslp.value is None:
            return "Pressure data not available"
        if self.station_pressure.value is None and self.mslp.value is not None:
            return f"MSLP {self.mslp}"
        if self.station_pressure.value is not None and self.mslp.value is None:
            return f"Station {self.station_pressure}"
        return f"{self.station_pressure}, MSLP {self.mslp}"

    @classmethod
    def from_json(
        cls, nws_json_data: dict[str, Any], unit: Optional[UnitInfo] = None
    ) -> Pressure:
        """Creates object from JSON data recieved from an NWS Observation."""
        pressure = _get_measurement(nws_json_data, "barometricPressure", unit)
        mslp = _get_measurement(nws_json_data, "seaLevelPressure", unit)
        return cls(station_pressure=pressure, mslp=mslp)


@dataclass
class RelativeLocation:
    """Metadata for a location relative to a point."""

    default_units = {
        "distance": unit_by_label("nautical mile"),
        "bearing": unit_by_label("degree"),
    }

    city: str
    state: str
    geometry: Optional[Point]
    distance: Measurement
    bearing: Measurement

    @classmethod
    def from_json(cls, nws_json_data: dict[str, Any]) -> RelativeLocation:
        """Creates object from JSON data recieved from an NWS Observation."""
        point = nws_json_data["geometry"]
        if not isinstance(point, Point):
            point = None
        city = nws_json_data.get("city")
        if not isinstance(city, str):
            city = ""
        state = nws_json_data.get("state")
        if not isinstance(state, str):
            state = ""
        distance = _get_measurement(
            nws_json_data, "distance", cls.default_units["distance"]
        )
        bearing = _get_measurement(
            nws_json_data, "bearing", cls.default_units["bearing"]
        )
        return cls(
            city=city,
            state=state,
            geometry=point,
            distance=distance,
            bearing=bearing,
        )


class Wind:
    """Dataclass for grouping of various wind observations."""

    _CARDINAL_DIRECTIONS = (
        "North",
        "North-Northeast",
        "Northeast",
        "East-Northeast",
        "East",
        "East-Southeast",
        "Southeast",
        "South-Southeast",
        "South",
        "South-Southwest",
        "Southwest",
        "West-Southwest",
        "West",
        "West-Northwest",
        "Northwest",
        "North-Northwest",
    )

    _CARDINAL_DIRECTIONS_ARROW = (
        "⬇",
        "⬇",
        "⬋",
        "⬅",
        "⬅",
        "⬅",
        "⬉",
        "⬆",
        "⬆",
        "⬆",
        "⬈",
        "➡",
        "➡",
        "➡",
        "⬊",
        "⬇",
    )

    _CARDINAL_DIRECTIONS_ABBR = (
        "N",
        "NNE",
        "NE",
        "ENE",
        "E",
        "ESE",
        "SE",
        "SSE",
        "S",
        "SSW",
        "SW",
        "WSW",
        "W",
        "WNW",
        "NW",
        "NNW",
    )

    def __init__(
        self, direction: Measurement, speed: Measurement, gust: Measurement
    ) -> None:
        self.direction = direction
        self.speed = speed
        self.gust = gust
        self._cardinal_index: Optional[int] = None
        if self.direction.value is not None:
            self._cardinal_index = int(round(self.direction.value / 22.5) % 16)

    def __str__(self) -> str:
        sb = ""
        if self.speed.value is None or self.speed.value == 0.0:
            sb = "No Wind"
        else:
            if self.direction.value is None:
                sb = f"Variable {self.speed}"
            else:
                sb = f"{self.cardinal_direction(style='arrow')} {self.speed}"
        if self.gust.value is not None and self.gust.value > 0:
            sb = f"{sb}, Gusts {self.gust}"
        return sb

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(direction={repr(self.direction)},"
            f" speed={repr(self.speed)}, gust={repr(self.gust)})"
        )

    @classmethod
    def from_json(
        cls, nws_json_data: dict[str, Any], unit: Optional[UnitInfo] = None
    ) -> Wind:
        """Creates object from JSON data recieved from an NWS Observation."""
        wdir = _get_measurement(nws_json_data, "windDirection")
        speed = _get_measurement(nws_json_data, "windSpeed", unit)
        gust = _get_measurement(nws_json_data, "windGust", unit)
        return cls(direction=wdir, speed=speed, gust=gust)

    def cardinal_direction(self, style: str = "short") -> Optional[str]:
        """
        The cardinal direction of the wind if available.

        Parameters:
        * style (str) -- The style of string to be returned. Possible values are
        'short', 'long', 'arrow'. Defaults to 'short'.

        Examples of each style for northeasterly wind:
        * 'short' -> 'NE'
        * 'long' -> 'Northeast'
        * 'arrow' -> '⬋'
        """
        if self._cardinal_index is not None:
            cfstyle = style.casefold()
            if cfstyle == "short":
                return self._CARDINAL_DIRECTIONS_ABBR[self._cardinal_index]
            elif cfstyle == "arrow":
                return self._CARDINAL_DIRECTIONS_ARROW[self._cardinal_index]
            elif cfstyle == "long":
                return self._CARDINAL_DIRECTIONS[self._cardinal_index]
        return None


@dataclass
class GridInformation:
    """
    A dataclass representing metadata for an NWS grid point.

    Attributes:
    * office_id (Optional[str]) -- The three letter identifier for the NWS
    forecast office. Defaults to None.
    * x (Optional[int]) -- X coordinate for the grid. Defaults to None.
    * y (Optional[int]) -- Y coordinate for the grid. Defaults to None.
    """

    office_id: Optional[str] = None
    x: Optional[int] = None
    y: Optional[int] = None


@dataclass
class MetarPhenomenon:
    """
    A dataclass representing a decoded METAR phenomena string.

    https://mediawiki.ivao.aero/index.php?title=METAR_explanation
    """

    INTENSITY_STRINGS = {"light": "Light", "heavy": "Heavy"}

    MODIFIER_STRINGS = {
        "patches": "Patches",
        "blowing": "Blowing",
        "low_drifting": "Low Drifting",
        "freezing": "Freezing",
        "shallow": "Shallow",
        "partial": "Partial",
        "showers": "Showers",
    }

    WEATHER_STRNGS = {
        "fog_mist": "Fog (Mist)",
        "dust_storm": "Dust Storm",
        "dust": "Dust",
        "drizzle": "Drizzle",
        "funnel_cloud": "Funnel Cloud",
        "fog": "Fog",
        "smoke": "Smoke",
        "hail": "Hail",
        "snow_pellets": "Snow Pellets",
        "haze": "Haze",
        "ice_crystals": "Ice Crystals",
        "ice_pellets": "Ice Pellets",
        "dust_whirls": "Dust Whirls",
        "spray": "Spray",
        "rain": "Rain",
        "sand": "Sand",
        "snow_grains": "Snow Grains",
        "snow": "Snow",
        "squalls": "Snow Squalls",
        "sand_storm": "Sand Storm",
        "thunderstorms": "Thunderstorms",
        "unknown": "Unknown Phenomena",
        "volcanic_ash": "Volcanic Ash",
    }

    raw_string: str
    weather: str
    intensity: Optional[str]
    modifier: Optional[str]
    in_vicinity: Optional[bool]

    def __str__(self) -> str:
        sb = "In Vicinity -- " if self.in_vicinity else ""
        if self.intensity in self.INTENSITY_STRINGS:
            sb = f"{sb}{self.INTENSITY_STRINGS[self.intensity]} "
        if self.weather in self.WEATHER_STRNGS:
            sb = f"{sb}{self.WEATHER_STRNGS[self.weather]} "
        if self.modifier in self.MODIFIER_STRINGS:
            sb = f"{sb[:-1]}, {self.MODIFIER_STRINGS[self.modifier]} "
        return sb.strip()

    @classmethod
    def from_json(cls, nws_json_data: dict[str, Any]) -> MetarPhenomenon:
        """Creates object from JSON data recieved from an NWS Observation."""
        raw = nws_json_data["rawString"]
        if not isinstance(raw, str):
            raise NwsDataError(f"Invalid METAR phenomenon raw string '{raw}'")
        weather = nws_json_data["weather"]
        if not isinstance(weather, str):
            raise NwsDataError(f"Invalid METAR phenomenon weather '{weather}'")
        intensity = nws_json_data["intensity"]
        if not isinstance(intensity, str):
            intensity = None
        modifier = nws_json_data["modifier"]
        if not isinstance(modifier, str):
            modifier = None
        in_vicinity = nws_json_data.get("inVicinity")
        if in_vicinity is not None and not isinstance(in_vicinity, bool):
            in_vicinity = None
        return cls(
            raw_string=raw,
            weather=weather,
            intensity=intensity,
            modifier=modifier,
            in_vicinity=in_vicinity,
        )


@dataclass
class CloudLayer:
    """
    A small dataclass representing a single cloud layer (METAR sky coverage).

    Attributes:
    * base (Measurement) -- Height of cloud layer above ground level.
    * amount (str) -- The METAR sky coverage amount.

    Properties:
    * amount_info (str) -- The METAR sky coverage amount descriptive info.
    """

    _METAR_SKY_COVERAGE = {
        "OVC": "Overcast",
        "BKN": "Broken",
        "SCT": "Scattered",
        "FEW": "Few",
        "SKC": "Clear",
        "CLR": "Clear",
        "VV": "Vertical Visibility",
    }

    base: Measurement
    amount: str

    def __str__(self) -> str:
        return f"{self.base} -- {self.amount_info}"

    @property
    def amount_info(self) -> str:
        """A descriptive string for the corresponding METAR abbreviation."""
        return self._METAR_SKY_COVERAGE[self.amount]

    @classmethod
    def from_json(
        cls, nws_json_data: dict[str, Any], unit: Optional[UnitInfo] = None
    ) -> CloudLayer:
        """Creates object from JSON data recieved from an NWS Observation."""
        base = _get_measurement(nws_json_data, "base", unit)
        amount = nws_json_data["amount"]
        if isinstance(amount, str):
            amount = amount.upper()
            if amount not in CloudLayer._METAR_SKY_COVERAGE:
                raise NwsDataError(f"Invalid cloud layer amount '{amount}'.")
        return cls(base=base, amount=amount)


class _NwsBase:
    """
    Metadata for an observation station, populated with data provided by the
    National Weather Service.
    """

    def __init__(self, nws_json_data: dict[str, Any]) -> None:
        self._raw_data = nws_json_data

    def __repr__(self) -> str:
        IGNORED_KEYS = "@context"
        sep = "\n    "
        sb = f"{self.__class__.__name__}({{"
        if len(self._raw_data) < 1:
            return f"{sb}}})"
        for k, v in self._raw_data.items():
            if k in IGNORED_KEYS:
                continue
            sb = f"{sb}{sep}'{k}': {repr(v)}"
        return f"{sb}\n}})"

    def __str__(self) -> str:
        return repr(self)

    @property
    def raw_data(self) -> dict[str, Any]:
        """Raw data from the National Weather service used for this object."""
        return self._raw_data

    def _get_str(self, key: str, null_empty: bool = False) -> Optional[str]:
        value = self._raw_data.get(key)
        if isinstance(value, str):
            if null_empty and len(value) < 1:
                return None
            return value
        return None

    def _get_time(self, key: str) -> Optional[datetime]:
        value = self._raw_data.get(key)
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        return None

    def _get_ref_urls(self, keys: Iterable[str]) -> dict[str, str]:
        urls: dict[str, str] = {}
        for key in keys:
            value = self._raw_data.get(key)
            if isinstance(value, str):
                if key == "@id":
                    urls["query"] = value
                else:
                    urls[key] = value
        return urls

    def _get_point(self, key: str) -> Optional[Point]:
        value = self._raw_data.get(key)
        if isinstance(value, str):
            point = wkt.loads(value)
            if isinstance(point, Point):
                return point
        return None

    def _get_timezone(self, key: str) -> Optional[tzinfo]:
        value = self._raw_data.get(key)
        if isinstance(value, str):
            tz = pytz.timezone(value)
            if isinstance(tz, tzinfo):
                return tz
        return None

    def _get_qv(
        self, key: str, convert_to: Optional[str] = None
    ) -> Optional[Measurement]:
        qvdict = self._raw_data.get(key)
        if isinstance(qvdict, dict) and all(isinstance(k, str) for k in qvdict):
            qv = Measurement.from_json(qvdict)
            if convert_to is None:
                return qv
            if convert_to is not None:
                qv.unit = unit_by_label(convert_to)
            return qv
        return None

    def _get_station_name(self) -> str:
        name = self._raw_data.get("name")
        if isinstance(name, str):
            return name
        return "Unknown Station Name"

    def _get_station_id(self) -> str:
        station_id = self._raw_data.get("stationIdentifier")
        if isinstance(station_id, str):
            return station_id
        station_id = self._raw_data.get("@id")
        if isinstance(station_id, str):
            return station_id.split("/")[-1]
        raise NwsDataError("Cannot determine stations ID.")


def _flatten_coords(point: Union[str, Point]) -> str:
    if isinstance(point, str):
        (lon, lat) = point.split(",")
        return f"{lon.strip()},{lat.strip()}"
    return f"{point.y},{point.x}"


def _get_google_link(point: Union[str, Point]) -> Optional[str]:
    if point is None:
        return None
    MAPS_URL = "https://www.google.com/maps/search/?api=1&query="
    location = _flatten_coords(point)
    return f"{MAPS_URL}{location}"


class ObservationStation(_NwsBase):
    """
    Metadata for an observation station, populated with data provided by the
    National Weather Service.
    """

    def __init__(self, nws_json_data: dict[str, Any], **params: Any) -> None:
        super().__init__(nws_json_data)
        self._identifier = self._get_station_id()
        self._name = self._get_station_name()
        url_keys = ("@id", "county", "fireWeatherZone", "forecast")
        self._reference_urls = self._get_ref_urls(url_keys)
        self._location = self._get_point("geometry")
        self._elevation = self._get_qv("elevation", "foot")
        self._timezone = self._get_timezone("timeZone")
        latest_obs = station_observations_latest(self._identifier, **params)
        self._latest_observations = Observation(latest_obs)
        self._google_maps_link = _get_google_link(self._location)

    def __str__(self) -> str:
        sep = "\n    "

        # Station information
        info_header = f"[{self._identifier}] {self._name}"
        sb = f"{info_header}\n"
        sb = f"{sb}{'-' * (len(info_header))}\n"
        if self._google_maps_link is not None:
            sb = f"{sb}  [Location]{sep}{self._google_maps_link}\n"
        if self._elevation is not None:
            sb = f"{sb}  [Elevation]{sep}{self._elevation}\n"
        if self._timezone is not None:
            sb = f"{sb}  [Timezone]{sep}{self._timezone}\n"

        # Observations
        # Try to use local time based on stations timezone
        obs_lines = str(self._latest_observations).splitlines(keepends=False)
        if len(obs_lines) >= 2 and self._timezone is not None:
            lt = self._latest_observations._timestamp.astimezone(self._timezone)
            time_str = lt.strftime("%D %H:%M %p")
            obs_lines[0] = f"[{time_str}] Latest Observations"
            obs_lines[1] = "-" * len(obs_lines[0])
        obs = "\n".join(obs_lines)
        sb = f"{sb}\n{obs}\n"

        return sb

    @classmethod
    def from_id(
        cls, station_id: str, proxies: Optional[dict[str, str]] = None
    ) -> ObservationStation:
        """
        Retrieves station data from the NWS API and constructs a populated
        ObservationStation object.

        Parameters:
        * station_id (str) -- The stations identifier.
        """
        return cls(stations_id(station_id, proxies=proxies), proxies=proxies)

    def update_latest_observations(self, **params: Any) -> None:
        """
        Retrieves the latest observations from the NWS API and updates object.
        """
        latest_obs = station_observations_latest(self._identifier, **params)
        self._latest_observations = Observation(latest_obs)

    @property
    def google_maps_link(self) -> Optional[str]:
        """A link to google maps at the stations location, if available."""
        return self._google_maps_link

    @property
    def latest_observations(self) -> Observation:
        """
        Retrieves the latest observations recorded by this station from the
        National Weather Service public API, from when this object was
        constructed. To retrieve an updated latest observation run
        update_latest_observations() method first.
        """
        return self._latest_observations

    @property
    def identifier(self) -> str:
        """The stations ID."""
        return self._identifier

    @property
    def name(self) -> str:
        """Descriptive name of the station."""
        return self._name

    @property
    def reference_urls(self) -> dict[str, str]:
        """
        Dictionary of reference API URLs, which may include:
        * 'query' -- The query used to populate this object.
        * 'county' -- A link to the NWS county zone containing this station.
        * 'fireWeatherZone' -- A link to the NWS fire weather forecast zone
        containing this station.
        * 'forecast' -- A link to the NWS public forecast zone containing this
        station.
        """
        return self._reference_urls

    @property
    def location(self) -> Optional[Point]:
        """The latitude and longitude of the station, if provided."""
        return self._location

    @property
    def elevation(self) -> Optional[Measurement]:
        """The elevation of the station with unit of measure, if provided."""
        return self._elevation

    @property
    def timezone(self) -> Optional[tzinfo]:
        """The timezone of the station, if provided."""
        return self._timezone


class Observation(_NwsBase):
    """
    Metadata for an observation, populated with data provided by the National
    Weather Service.
    """

    default_units = {
        "temperature": unit_by_label("fahrenheit"),
        "pressure": unit_by_label("hectopascal"),
        "wind": unit_by_label("knot"),
        "precipitation": unit_by_label("inch"),
    }

    def __init__(self, nws_json_data: dict[str, Any]) -> None:
        super().__init__(nws_json_data)
        url_keys = ("@id", "station")
        self._reference_urls = self._get_ref_urls(url_keys)
        self._temperature = Temperature.from_json(
            self._raw_data, self.default_units["temperature"]
        )
        self._pressure = Pressure.from_json(
            self._raw_data, self.default_units["pressure"]
        )
        self._wind = Wind.from_json(self._raw_data, self.default_units["wind"])
        self._precipitation = Precipitation.from_json(
            self._raw_data, self.default_units["precipitation"]
        )
        ts = self._get_time("timestamp")
        if ts is None:
            raise NwsDataError("No timestamp for observations found!")
        self._timestamp = ts
        self._metar = self._get_str("rawMessage", null_empty=True)
        self._description = self._get_str("textDescription", null_empty=True)
        self._location = self._get_point("geometry")
        self._elevation = self._get_qv("elevation", "foot")
        self._visibility = self._get_qv("visibility", "mile us statute")
        self._cloud_layers = self._get_clouds()
        self._present_weather = self._get_phenoms()

    def __str__(self) -> str:
        sep = "\n    "

        # Header
        time_str = self._timestamp.strftime("%D %H:%M %p")
        header = f"[{time_str}] Latest Observations"
        sb = f"{header}\n"
        sb = f"{sb}{'-' * (len(header))}\n"

        # Observations
        if self._metar is not None:
            sb = f"{sb}  [METAR]{sep}{self._metar}\n"
        sb = f"{sb}  [Temperature]{sep}{self._temperature}\n"
        sb = f"{sb}  [Pressure]{sep}{self._pressure}\n"
        sb = f"{sb}  [Wind]{sep}{self._wind}\n"
        if self._precipitation is not None:
            sb = f"{sb}  [Precipitation]{sep}{self._precipitation}\n"
        if self._visibility is not None:
            sb = f"{sb}  [Visibility]{sep}{self._visibility}\n"
        if self._cloud_layers is not None:
            if len(self._cloud_layers) > 0:
                sb = f"{sb}  [Cloud Layers]"
                for layer in self._cloud_layers:
                    sb = f"{sb}{sep}{layer}"
                sb = f"{sb}\n"
        if self._present_weather is not None:
            sb = f"{sb}  [Present Weather Phenomena]"
            for phenom in self._present_weather:
                sb = f"{sb}{sep}{phenom}"
            sb = f"{sb}\n"

        return sb

    def _get_phenoms(self) -> Optional[tuple[MetarPhenomenon, ...]]:
        phenoms = self._raw_data.get("presentWeather")
        if isinstance(phenoms, Iterable):
            decoded = tuple(MetarPhenomenon.from_json(i) for i in phenoms)
            if len(decoded) > 0:
                return decoded
            return None
        return None

    def _get_clouds(self) -> Optional[tuple[CloudLayer, ...]]:
        layers = self._raw_data.get("cloudLayers")
        if isinstance(layers, Iterable):
            return tuple(CloudLayer.from_json(layer) for layer in layers)
        return None

    @property
    def present_weather(self) -> Optional[tuple[MetarPhenomenon, ...]]:
        """A collection of decoded METAR weather phenomena, if provided."""
        return self._present_weather

    @property
    def cloud_layers(self) -> Optional[tuple[CloudLayer, ...]]:
        """Observed cloud layers, if provided."""
        return self._cloud_layers

    @property
    def elevation(self) -> Optional[Measurement]:
        """
        The elevation origin of the observations with unit of measure, if
        provided.
        """
        return self._elevation

    @property
    def location(self) -> Optional[Point]:
        """
        The location (latitude, longitude) origin of the observations, if
        provided. May be slightly different from the parent stations location.
        """
        return self._location

    @property
    def description(self) -> Optional[str]:
        """Descriptive text for the observation, if available."""
        return self._description

    @property
    def metar(self) -> Optional[str]:
        """
        The raw METAR message, if available. Note that many mesonet stations
        that update every 10 minutes often do not have METARs.
        """
        return self._metar

    @property
    def timestamp(self) -> datetime:
        """
        The time when observations were recorded. This is not guaranteed to have
        a valid timezone with it, but usually is in UTC or a UTC offset. You may
        need to check the parent stations timezone to get a true local time.
        """
        return self._timestamp

    @property
    def reference_urls(self) -> dict[str, str]:
        """
        Dictionary of reference API URLs, which may include:
        * 'query' -- The query used to populate this object.
        * 'station' -- A link to the observation station.
        """
        return self._reference_urls

    @property
    def temperature(self) -> Temperature:
        """All temperature readings in the observation."""
        return self._temperature

    @property
    def pressure(self) -> Pressure:
        """All barometric pressure readings in the observation."""
        return self._pressure

    @property
    def wind(self) -> Wind:
        """All wind readings in the observation."""
        return self._wind

    @property
    def precipitation(self) -> Optional[Precipitation]:
        """Precipitation totals over the past 6 hours, if available."""
        return self._precipitation

    @property
    def visibility(self) -> Optional[Measurement]:
        """The visibility distance with unit of measure, if available."""
        return self._visibility


class PointInformation(_NwsBase):
    """
    Information, such as various links and forecasting offices, for a specified
    location (latitude, longitude).
    """

    def __init__(self, nws_json_data: dict[str, Any]) -> None:
        super().__init__(nws_json_data)
        url_keys = (
            "@id",
            "forecast",
            "forecastOffice",
            "forecastHourly",
            "forecastGridData",
            "observationStations",
            "forecastZone",
            "county",
            "fireWeatherZone",
        )
        self._reference_urls = self._get_ref_urls(url_keys)
        self._grid_info = GridInformation(
            office_id=nws_json_data.get("gridId"),
            x=nws_json_data.get("gridX"),
            y=nws_json_data.get("gridY"),
        )
        self._county_warning_area = self._get_str("cwa", null_empty=True)
        self._location = self._get_point("geometry")
        self._google_maps_link = _get_google_link(self._location)
        self._timezone = self._get_timezone("timeZone")
        self._radar_station = self._get_str("radarStation", null_empty=True)
        self._relative_location = self._get_loc("relativeLocation")

    def _get_loc(self, key: str) -> Optional[RelativeLocation]:
        value = self._raw_data.get(key)
        if isinstance(value, dict):
            return RelativeLocation.from_json(value)
        return None

    @classmethod
    def from_point(cls, point: Union[str, Point]) -> PointInformation:
        """
        Retrieves points data from the NWS API and constructs a populated
        PointInformation object.

        Parameters:
        * point (str | Point) -- The coordinates of the point to inspect.

        If point is a str, it is required to be comma seperated latitude and
        longitude values, ie '{lon},{lat}'. Otherwise, a Point object will be
        assumed, and should work as long as the object has an 'x' and 'y'
        attribute in form x=lon and y=lat (this is how points from the NWS are
        presented).
        """
        if isinstance(point, str):
            (lon, lat) = point.split(",")
            data = points(f"{lon.strip()},{lat.strip()}")
        else:
            data = points(f"{point.y},{point.x}")
        return cls(data)

    @property
    def relative_location(self) -> Optional[RelativeLocation]:
        """
        Information for a location relative to the input point, if available.
        Typically the town or city center in which the point exists.
        """
        return self._relative_location

    @property
    def county_warning_area(self) -> Optional[str]:
        """
        The three letter identifier for the NWS forecast office for this area.
        """
        return self._county_warning_area

    @property
    def radar_station(self) -> Optional[str]:
        """The nearest radar station identifier, if available."""
        return self._radar_station

    @property
    def grid_info(self) -> GridInformation:
        """Information on NWS grid points for this location."""
        return self._grid_info

    @property
    def reference_urls(self) -> dict[str, str]:
        """
        Dictionary of reference API URLs, which may include:
        * 'query' -- The query used to populate this object.
        * 'forecast'
        * 'forecastOffice'
        * 'forecastHourly'
        * 'forecastGridData'
        * 'observationStations'
        * 'forecastZone'
        * 'county'
        * 'fireWeatherZone'
        """
        return self._reference_urls

    @property
    def location(self) -> Optional[Point]:
        """
        The location (latitude, longitude) origin, if available. Should be close
        to or identical to the input coordinates.
        """
        return self._location

    @property
    def google_maps_link(self) -> Optional[str]:
        """
        A link to google maps at the location, if available. If location is
        None, this will also return None.
        """
        return self._google_maps_link

    @property
    def timezone(self) -> Optional[tzinfo]:
        """The timezone of the location, if provided."""
        return self._timezone
