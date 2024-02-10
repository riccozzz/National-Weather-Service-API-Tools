"""
Experimenting with parsing METAR data into a python object.
"""
from __future__ import annotations
from typing import Any


def _quotify(value: Any) -> str:
    """
    Returns str(value), if input value is already a string we wrap it in single
    quotes.
    """
    return f"'{value}'" if isinstance(value, str) else str(value)


def _is_fraction(value: str) -> bool:
    """
    Tries to determine if a string is a fractional number. Note that whitespace
    will not be removed and will likely return False if any exists.
    """
    split_values = value.split("/", maxsplit=1)
    if len(split_values) > 1:
        if split_values[0].isdigit() and split_values[1].isdigit():
            return True
    return False


class MetarRemarks:
    """
    Python object for storing and decoding remarks in a standard METAR message.
    """

    # TODO: Error handling instead of returning None
    # TODO: Actually check for valid data

    def __init__(self, metar_remarks: str) -> None:
        """
        Creates a MetarRemarks object with the given string of remarks from a
        standard METAR message.

        Parameters:
        * metar_remarks (str) -- METAR remarks
        """
        self.remarks = metar_remarks.upper()
        self.type_of_station = "AO2" if "AO2" in self.remarks else None
        self.peak_wind = self._get_by_search(self.remarks, "PK WND ")
        self.wind_shift = self._get_by_search(self.remarks, "WSHFT ")
        self.tower_visibility = self._get_by_search(self.remarks, "TWR VIS ")
        self.surface_visibility = self._get_by_search(self.remarks, "SFC VIS ")
        self.variable_visibility, self.alternate_visibility = self._get_visibilities(
            self.remarks
        )
        self.lightning = self._get_lightning(self.remarks)

    def __repr__(self) -> str:
        sb = f"{self.__class__.__name__}("
        sb = f"{sb}type_of_station={_quotify(self.type_of_station)}"
        sb = f"{sb}, peak_wind={_quotify(self.peak_wind)}"
        sb = f"{sb}, wind_shift={_quotify(self.wind_shift)}"
        sb = f"{sb}, tower_visibility={_quotify(self.tower_visibility)}"
        sb = f"{sb}, surface_visibility={_quotify(self.surface_visibility)}"
        sb = f"{sb}, variable_visibility={_quotify(self.variable_visibility)}"
        sb = f"{sb}, alternate_visibility={_quotify(self.alternate_visibility)}"
        sb = f"{sb}, lightning={_quotify(self.lightning)}"
        return f"{sb})"

    def __str__(self) -> str:
        return self.remarks

    def _get_by_search(self, metar_remarks: str, search_str: str) -> str | None:
        index = metar_remarks.find(search_str)
        if index == -1:
            return None
        index += len(search_str)
        end_index = metar_remarks[index:].find(" ") + index
        return metar_remarks[index:end_index]

    def _get_visibilities(self, metar_remarks: str) -> tuple[str | None, str | None]:
        # Set both as None by default
        variable_vis = None
        alternate_vis = None
        # Need to loop across the string since the two signatures are similar
        vis_index = 0
        while True:
            vis_index = metar_remarks.find("VIS ", vis_index)
            if vis_index == -1:
                break
            vis_index += 4
            rmks_split = metar_remarks[vis_index:].split(maxsplit=2)
            rmks_len = len(rmks_split)
            if rmks_len < 1:
                break
            if "V" in rmks_split[0]:
                variable_vis = rmks_split[0]
                if rmks_len > 1 and _is_fraction(rmks_split[1]):
                    variable_vis = f"{variable_vis} {rmks_split[1]}"
            else:
                if rmks_len < 2:
                    continue
                alternate_vis = f"{rmks_split[0]} {rmks_split[1]}"
        return (variable_vis, alternate_vis)

    def _get_lightning(self, metar_remarks: str) -> str | None:
        ltg_index = metar_remarks.find("LTG")
        if ltg_index == -1:
            return None
        # Handle special case of automated distant lightning first
        # Format is LTG DSNT <DIR>
        if "LTG DSNT " in metar_remarks:
            end_index = metar_remarks.find(" ", ltg_index + 9)
            return metar_remarks[ltg_index:end_index]
        # Handle manual station lightning
        freq_index = metar_remarks.rfind(" ", 0, ltg_index - 1) + 1
        if freq_index == 0:
            return None
        loc_index = metar_remarks.find(" ", ltg_index) + 1
        if loc_index == 0:
            return None
        end_loc_index = metar_remarks.find(" ", loc_index)
        if end_loc_index == -1:
            return metar_remarks[freq_index:]
        return metar_remarks[freq_index:end_loc_index]


class MetarRemarksL:
    """
    Python object for storing and decoding remarks in a standard METAR message.
    """

    def __init__(self, metar_remarks: str) -> None:
        self.remarks = metar_remarks.strip().upper()
        self.remaining = self.remarks.split()
        self.type_of_station = self._pop_type_of_station(self.remaining)
        self.peak_wind = self._pop_next_next(self.remaining, "PK", "WND")
        self.wind_shift = self._pop_next(self.remaining, "WSHFT")
        self.tower_visibility = self._pop_next_next(self.remaining, "TWR", "VIS")
        self.surface_visibility = self._pop_next_next(self.remaining, "SFC", "VIS")

    def __repr__(self) -> str:
        sb = f"{self.__class__.__name__}("
        sb = f"{sb}type_of_station={_quotify(self.type_of_station)}"
        sb = f"{sb}, peak_wind={_quotify(self.peak_wind)}"
        sb = f"{sb}, wind_shift={_quotify(self.wind_shift)}"
        sb = f"{sb}, tower_visibility={_quotify(self.tower_visibility)}"
        sb = f"{sb}, surface_visibility={_quotify(self.surface_visibility)}"
        return f"{sb})"

    def __str__(self) -> str:
        return self.remarks

    def _pop_type_of_station(self, remarks: list[str]) -> str | None:
        try:
            remarks.remove("AO2")
            return "AO2"
        except ValueError:
            return None

    def _pop_next(self, remarks: list[str], search: str) -> str | None:
        try:
            index = remarks.index(search)
            next_val = remarks[index + 1]
            end_index = index + 2
            del remarks[index:end_index]
            return next_val
        except (ValueError, IndexError):
            return None

    def _pop_next_next(self, remarks: list[str], first: str, second: str) -> str | None:
        try:
            first_index = remarks.index(first)
            if remarks[first_index + 1] != second:
                return None
            value = remarks[first_index + 2]
            end_index = first_index + 3
            del remarks[first_index:end_index]
            return value
        except (ValueError, IndexError):
            return None


class MetarObservation:
    """
    Python object for storing and decoding a standard METAR message.
    """

    _report_types = {
        "METAR": "Hourly (scheduled) report",
        "SPECI": "Special (unscheduled) report",
    }

    _report_mods = {
        "AUTO": "Fully automated report",
        "COR": "Correction of previous report",
    }

    _sky_conditions = {
        "CLR": "Clear",
        "FEW": "Few",
        "SCT": "Scattered",
        "BKN": "Broken",
        "OVC": "Overcast",
        "VV": "Vertical Visibility",
    }

    def __init__(self, metar_observation: str) -> None:
        """
        Creates a MetarObservation object with the given observation string.

        Parameters:
        * metar_observation (str) -- Full METAR observation string
        """
        # Split off remarks section
        obs_split = metar_observation.upper().split(" RMK ", maxsplit=2)
        # Split observations out into a list and quickly check length
        observations = obs_split[0].split()
        if len(observations) < 7:
            raise RuntimeError(
                "Invalid METAR string, not enough parts "
                f"({len(observations)} < 7) to be valid."
            )
        # These must be sequential
        self.report_type = self._pop_report_type(observations)
        self.station_id = self._pop_station(observations)
        self.date_time = self._pop_date_time(observations)
        self.report_modifier = self._pop_report_mod(observations)
        self.wind = self._pop_wind(observations)
        self.visibility = self._pop_visibility(observations)
        self.runway_visual_range = self._pop_runway_visual(observations)
        # We now start from the back of the remaining list
        self.altimeter = self._pop_altimeter(observations)
        self.temperature = self._pop_temp_dew(observations)
        self.sky_condition = self._pop_sky_condition(observations)
        self.weather_phenomena = self._pop_weather_phenom(observations)
        # Remarks
        if len(obs_split) > 1:
            self.remarks = MetarRemarks(metar_remarks=obs_split[1])
        else:
            self.remarks = None

    def __repr__(self) -> str:
        sb = f"{self.__class__.__name__}(\n"
        sb = f"{sb}    report_type={_quotify(self.report_type)},\n"
        sb = f"{sb}    station_id={_quotify(self.station_id)},\n"
        sb = f"{sb}    date_time={_quotify(self.date_time)},\n"
        sb = f"{sb}    report_modifier={_quotify(self.report_modifier)},\n"
        sb = f"{sb}    wind={_quotify(self.wind)},\n"
        sb = f"{sb}    visibility={_quotify(self.visibility)},\n"
        sb = f"{sb}    runway_visual_range={_quotify(self.runway_visual_range)},\n"
        sb = f"{sb}    weather_phenomena={_quotify(self.weather_phenomena)},\n"
        sb = f"{sb}    sky_condition={_quotify(self.sky_condition)},\n"
        sb = f"{sb}    temperature={_quotify(self.temperature)},\n"
        sb = f"{sb}    altimeter={_quotify(self.altimeter)},\n"
        sb = f"{sb}    remarks={_quotify(str(self.remarks))},\n"
        return f"{sb})"

    def __str__(self) -> str:
        if self.report_type is not None:
            sb = self.report_type
        else:
            sb = ""
        sb = f"{sb} {self.station_id}"
        sb = f"{sb} {self.date_time}"
        if self.report_modifier is not None:
            sb = sb = f"{sb} {self.report_modifier}"
        sb = f"{sb} {self.wind}"
        sb = f"{sb} {self.visibility}"
        if self.runway_visual_range is not None:
            sb = f"{sb} {self.runway_visual_range}"
        if self.weather_phenomena is not None:
            sb = f"{sb} {self.weather_phenomena}"
        sb = f"{sb} {self.sky_condition}"
        sb = f"{sb} {self.temperature}"
        sb = f"{sb} {self.altimeter}"
        if self.remarks is not None:
            sb = f"{sb} RMK {self.remarks}"
        return sb.strip()

    def _pop_report_type(self, observations: list[str]) -> str | None:
        if observations[0] in self._report_types:
            return observations.pop(0)
        return None

    def _pop_station(self, observations: list[str]) -> str:
        station_id = observations.pop(0)
        if len(station_id) != 4:
            raise RuntimeError(
                f"Invalid station ID '{station_id}', "
                "should be the 4 character ICAO location id."
            )
        return station_id

    def _pop_date_time(self, observations: list[str]) -> str:
        date_time = observations.pop(0)
        if len(date_time) != 7:
            raise RuntimeError(
                f"Invalid date/time '{date_time}', not 7 ({len(date_time)}) characters."
            )
        if date_time[-1] != "Z":
            raise RuntimeError(f"Invalid date/time '{date_time}', does not end in 'Z'.")
        return date_time

    def _pop_report_mod(self, observations: list[str]) -> str | None:
        if observations[0] in self._report_mods:
            return observations.pop(0)
        return None

    def _pop_wind(self, observations: list[str]) -> str:
        wind_dir_spd = observations.pop(0)
        if len(wind_dir_spd) < 7:
            raise RuntimeError(
                f"Invalid wind speed/direction '{wind_dir_spd}',"
                f" length is too short ({len(wind_dir_spd)} < 7)."
            )
        if not wind_dir_spd.endswith("KT"):
            raise RuntimeError(
                f"Invalid wind speed/direction '{wind_dir_spd}',"
                " string does not end in KT."
            )
        if len(observations[0]) == 7 and observations[0][3] == "V":
            wind_dir_spd = f"{wind_dir_spd} {observations.pop(0)}"
        return wind_dir_spd

    def _pop_visibility(self, observations: list[str]) -> str:
        visibility = observations.pop(0)
        if not visibility.endswith("SM"):
            raise RuntimeError(
                f"Invalid visibility '{visibility}', string does not end in SM."
            )
        return visibility

    def _pop_runway_visual(self, observations: list[str]) -> str | None:
        if observations[0].endswith("FT"):
            return observations.pop(0)
        return None

    def _pop_altimeter(self, observations: list[str]) -> str:
        altimeter = observations.pop()
        if len(altimeter) != 5:
            raise RuntimeError(
                f"Invalid altimeter '{altimeter}', not 5 ({len(altimeter)}) characters."
            )
        if altimeter[0] != "A":
            raise RuntimeError(
                f"Invalid altimeter '{altimeter}', does not start in 'A'."
            )
        return altimeter

    def _pop_temp_dew(self, observations: list[str]) -> str:
        temp_dew = observations.pop()
        if temp_dew[2] != "/" and temp_dew[3] != "/":
            raise RuntimeError(
                f"Invalid temperature/dew point '{temp_dew}', '/' in wrong position."
            )
        return temp_dew

    def _pop_sky_condition(self, observations: list[str]) -> str:
        sky_condition = ""
        for metar_part in reversed(observations):
            if len(metar_part) < 3:
                break
            if metar_part[0:3] not in self._sky_conditions:
                break
            sky_condition = f"{observations.pop()} {sky_condition}"
        return sky_condition.strip()

    def _pop_weather_phenom(self, observations: list[str]) -> str | None:
        if len(observations) < 1:
            return None
        return " ".join(observations)

    # def _parse_date_time(self, date_time: str) -> datetime:
    #     current_date = datetime.now()
    #     day_of_month = int(date_time[0:2])
    #     hour = int(date_time[2:4])
    #     minute = int(date_time[4:6])
    #     return datetime(
    #         year=current_date.year,
    #         month=current_date.month,
    #         day=day_of_month,
    #         hour=hour,
    #         minute=minute,
    #         tzinfo=timezone.utc,
    #     )
