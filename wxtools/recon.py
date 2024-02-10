"""
Decoding of tropical cyclone aircraft recon. missions and text products
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.table import Table

from .nws import Measurement
from .units import unit_by_wmo

HDOB_EXAMPLE = """000
URNT15 KNHC 281857
AF307 2909A IAN                HDOB 24 20220928
184800 2644N 08305W 6969 03036 //// +074 //// 008066 070 062 015 01
184830 2644N 08304W 6967 03034 //// +071 //// 005066 069 064 016 01
184900 2644N 08302W 6970 03024 //// +066 //// 005067 069 066 015 01
184930 2644N 08300W 6965 03023 //// +067 //// 005068 069 067 012 01
185000 2644N 08258W 6965 03014 //// +075 //// 004069 072 069 009 01
185030 2644N 08256W 6969 03002 //// +080 //// 004065 066 071 009 01
185100 2644N 08254W 6967 02997 //// +080 //// 002067 069 075 008 01
185130 2644N 08253W 6970 02985 //// +079 //// 006071 077 077 007 01
185200 2644N 08251W 6968 02978 //// +076 //// 014081 083 079 012 01
185230 2644N 08249W 6961 02974 //// +084 //// 015078 083 081 010 01
185300 2644N 08247W 6971 02951 //// +078 //// 014071 075 083 018 01
185330 2644N 08246W 6967 02945 //// +076 //// 014080 084 084 021 01
185400 2644N 08244W 6980 02916 //// +075 //// 020093 094 089 044 01
185430 2644N 08243W 6962 02922 //// +075 //// 023091 096 092 045 01
185500 2644N 08241W 6964 02905 //// +074 //// 021083 086 098 048 01
185530 2644N 08239W 6956 02899 //// +071 //// 022088 092 103 052 01
185600 2644N 08238W 6961 02873 //// +074 //// 027096 104 105 047 01
185630 2644N 08236W 6969 02847 //// +076 //// 034096 103 113 042 01
185700 2644N 08235W 6946 02859 //// +076 //// 038102 108 112 036 01
185730 2644N 08234W 6978 02804 //// +077 //// 042103 110 112 034 01
$$
;"""

HDOB_NEW_EXAMPLE = """244
URNT15 KNHC 121303
AF302 0214A KARL               HDOB 30 20221012
125400 2051N 09403W 8434 01569 0106 +160 +143 214030 034 034 006 00
125430 2052N 09405W 8434 01568 0106 +160 +144 217030 030 036 005 00
125500 2053N 09406W 8433 01568 0104 +160 +143 217032 033 036 006 03
125530 2054N 09407W 8434 01564 0103 +157 +143 214033 034 036 006 03
125600 2056N 09408W 8433 01564 0105 +152 +143 213035 036 036 006 03
125630 2057N 09410W 8431 01565 0106 +149 +147 213035 036 037 018 03
125700 2058N 09411W 8436 01559 0109 +144 +143 213035 037 037 024 00
125730 2059N 09412W 8434 01564 0104 +150 +146 210033 035 038 023 03
125800 2100N 09413W 8432 01565 0092 +170 +139 212032 033 033 004 00
125830 2102N 09415W 8436 01558 0090 +170 +132 211034 034 033 003 00
125900 2103N 09416W 8436 01558 0088 +172 +140 214034 035 032 004 00
125930 2104N 09417W 8467 01529 0098 +161 +153 213035 036 030 004 00
130000 2105N 09419W 8683 01315 0100 +173 +166 213034 038 030 003 00
130030 2107N 09420W 8938 01060 0095 +187 +180 207035 036 033 003 00
130100 2108N 09421W 9164 00844 0094 +194 +194 211035 039 033 005 03
130130 2109N 09422W 9256 00749 0081 +213 +192 214036 037 031 003 00
130200 2110N 09424W 9250 00751 0078 +215 +186 214039 040 033 002 00
130230 2111N 09425W 9253 00750 0078 +215 +188 213038 040 034 002 00
130300 2112N 09426W 9254 00745 0075 +216 +183 215036 036 035 002 00
130330 2114N 09427W 9257 00741 0073 +215 +186 218036 037 035 000 00
$$
;"""


class HDOBDataError(Exception):
    """Exception for issues decoding raw HDOB data."""


@dataclass
class GeoPoint:
    latitude: float
    longitude: float

    def __str__(self) -> str:
        if self.latitude > 0:
            lat_str = f"{self.latitude:.2f}N"
        else:
            lat_str = f"{self.latitude * -1:.2f}S"
        if self.longitude > 0:
            lon_str = f"{self.longitude:.2f}E"
        else:
            lon_str = f"{self.longitude * -1:.2f}W"
        return f"{lat_str} {lon_str}"


class HighDensityMessage:

    _data_types = {
        "UR": "Horizontal Observations",
        "UZ": "Vertical Observations",
    }
    _basins = {
        "NT": "Atlantic",
        "PN": "Eastern/Central Pacific",
        "PA": "Western Pacific",
    }
    _icaos = {
        "KNHC": "National Hurricane Center",
        "KBIX": "Keesler Air Force Base",
        "KWBC": "National Weather Service HQ",
    }
    _aircraft = {
        "AF300": "Air Force C130J Hercules",
        "AF301": "Air Force C130J Hercules",
        "AF302": "Air Force C130J Hercules",
        "AF303": "Air Force C130J Hercules",
        "AF304": "Air Force C130J Hercules",
        "AF305": "Air Force C130J Hercules",
        "AF306": "Air Force C130J Hercules",
        "AF307": "Air Force C130J Hercules",
        "AF308": "Air Force C130J Hercules",
        "NOAA2": "NOAA WP-3D Orion 'Kermit'",
        "NOAA3": "NOAA WP-3D Orion 'Miss Piggy'",
        "NOAA9": "NOAA Gulfstream 'Gonzo'",
    }
    _storm_locations = {
        "A": "Atlantic, Caribbean, or Gulf of Mexico",
        "E": "Eastern Pacific",
        "C": "Central Pacific",
        "W": "Western Pacific",
    }

    def __init__(self, raw_hdob: str) -> None:
        self.raw_data = raw_hdob.strip().upper()

        raw_lines = [ln.strip() for ln in self.raw_data.splitlines()]
        if len(raw_lines) < 5:
            raise HDOBDataError("Not enough lines for a valid HDOB.")
        if len(raw_lines[0]) == 3:
            raw_lines.pop(0)

        self._parse_comm_header(raw_lines[0])
        self._parse_mission_header(raw_lines[1])

        full_date = f"{self.date_string}{self.time_string[2:]}"
        self.timestamp = datetime.strptime(full_date, "%Y%m%d%H%M")

        self.observations: list[HighDensityObservation] = []
        for line in raw_lines[2:]:
            if line == "$$" or line == ";":
                break
            self.observations.append(HighDensityObservation(line, self.timestamp))

    def pretty_print(self) -> None:

        console = Console()
        table = Table(
            title="High Density Observations",
            caption="Some Caption Down Here",
            show_header=True,
        )

        table.add_column("Timestamp")
        table.add_column("Coordinates")
        table.add_column("Geopotential Height", max_width=12)
        table.add_column("Flight Level Pressure", max_width=10)
        table.add_column("Extrapolated Pressure", max_width=12)
        table.add_column("Flight Level Temp", max_width=10)
        table.add_column("Flight Level Dewpoint", max_width=10)
        table.add_column("Flight Level Wind", max_width=20)
        table.add_column("Flight Level Wind Peak", max_width=10)
        table.add_column("SFMR Wind Peak", max_width=10)
        table.add_column("SFMR Rain Rate", max_width=10)

        for obs in self.observations:
            table.add_row(
                f"{obs.timestamp.time()}Z",
                f"{obs.coordinates}",
                f"{obs.geopotential_height}",
                f"{obs.fl_pressure}",
                f"{obs.extrap_pressure}",
                f"{obs.fl_temperature}",
                f"{obs.fl_dewpoint}",
                f"{obs.fl_wind_direction} @ {obs.fl_wind_speed}",
                f"{obs.fl_wind_peak}",
                f"{obs.sfmr_wind_peak}",
                f"{obs.sfmr_rain_rate}",
            )

        console.print(table)

    def __str__(self) -> str:

        lines = [
            f"Observations at {self.timestamp}",
            "",
            "[Communications Header]",
        ]

        dtype = self._data_types.get(self.data_type, "Unknown")
        lines.append(f"  Data Type -- {self.data_type} ({dtype})")
        basin = self._basins.get(self.basin, "Unknown")
        lines.append(f"  Basin -- {self.basin} ({basin})")
        lines.append(f"  Product Index Number -- {self.product_index_number}")
        icao = self._icaos.get(self.icao, "Unknown")
        lines.append(f"  ICAO -- {self.icao} ({icao})")
        lines.append(f"  Time String -- {self.time_string}")
        lines.append("")

        lines.append("[Mission Header]")
        aircraft = self._aircraft_desc()
        lines.append(f"  Aircraft ID -- {self.aircraft_id} ({aircraft})")
        seq = self._seq_desc()
        lines.append(f"  Mission Sequence -- {self.mission_sequence} ({seq})")
        stormid = self._storm_id_desc()
        lines.append(f"  Storm ID -- {self.storm_short_id} ({stormid})")
        loc = self._location_desc()
        lines.append(f"  Storm Location -- {self.storm_short_location} ({loc})")
        lines.append(f"  Storm Name -- {self.storm_name}")
        lines.append(f"  Observation Number -- {self.observation_number}")
        lines.append(f"  Date String -- {self.date_string}")
        lines.append("")

        lines.append("[Observations]")
        for obs in self.observations:
            lines.append(f"  {obs}")

        return "\n".join(lines)

    def _location_desc(self) -> str:
        return self._storm_locations.get(self.storm_short_location, "Unknown")

    def _aircraft_desc(self) -> str:
        if self.aircraft_id in self._aircraft:
            return self._aircraft[self.aircraft_id]
        if self.aircraft_id.startswith("NOAA"):
            return "NOAA"
        if self.aircraft_id.startswith("AF"):
            return "Air Force"
        return "Unknown"

    def _seq_desc(self) -> str:
        if self.mission_sequence == "WX":
            return "Non-tasked mission"
        try:
            return f"Tasked mission #{int(self.mission_sequence)}"
        except ValueError:
            pass
        if self.mission_sequence[0] == "W":
            missno = ord(self.mission_sequence[1]) - 64
            return f"Non-tasked mission #{missno}"
        return "Unknown"

    def _storm_id_desc(self) -> str:
        if self.storm_short_id == "WX":
            return "Unclassified"
        try:
            return f"Storm #{int(self.storm_short_id)}"
        except ValueError:
            pass
        if self.storm_short_id[0] == self.storm_short_id[1]:
            storm_no = ord(self.storm_short_id[0]) - 64
            return f"Unclassifed Storm #{storm_no}"
        return "Unknown"

    def _parse_comm_header(self, comm_header: str) -> None:
        # Example: 'URNT15 KNHC 281857'
        comm_split = comm_header.split()
        if len(comm_split) != 3:
            raise HDOBDataError(
                "Invalid communications header, expecting 3 data elements."
            )
        if len(comm_split[0]) != 6:
            raise HDOBDataError(
                "Invalid communications header, expecting"
                " 6 characters in first data element."
            )
        if len(comm_split[2]) != 6:
            raise HDOBDataError(
                "Invalid communications header, expecting"
                " 6 characters in third data element."
            )
        self.data_type = comm_split[0][0:2]
        self.basin = comm_split[0][2:4]
        self.product_index_number = int(comm_split[0][4:6])
        self.icao = comm_split[1]
        self.time_string = comm_split[2]

    def _parse_mission_header(self, mission_header: str) -> None:
        # Example: 'AF307 2909A IAN                HDOB 24 20220928'
        mission_split = mission_header.split()
        if len(mission_split) != 6:
            raise HDOBDataError("Invalid mission header, expecting 6 data elements.")
        if len(mission_split[0]) != 5:
            raise HDOBDataError(
                "Invalid mission header, expecting"
                " 5 characters in first data element."
            )
        if len(mission_split[1]) != 5:
            raise HDOBDataError(
                "Invalid mission header, expecting"
                " 5 characters in second data element."
            )
        if mission_split[3] != "HDOB":
            raise HDOBDataError("Invalid mission header, HDOB not specified.")
        try:
            obs_num = int(mission_split[4])
        except ValueError as ex:
            raise HDOBDataError(
                "Invalid mission header, could not get "
                "observation number from 4th data element."
            ) from ex

        self.aircraft_id = mission_split[0]
        self.mission_sequence = mission_split[1][0:2]
        self.storm_short_id = mission_split[1][2:4]
        self.storm_short_location = mission_split[1][4]
        self.storm_name = mission_split[2]
        self.observation_number = obs_num
        self.date_string = mission_split[5]


class HighDensityObservation:

    _hpa_unit_info = unit_by_wmo("hPa")
    _meters_unit_info = unit_by_wmo("m")
    _celsius_unit_info = unit_by_wmo("degC")
    _degrees_unit_info = unit_by_wmo("degree_(angle)")
    _knots_unit_info = unit_by_wmo("kt")
    _mmhr_unit_info = unit_by_wmo("mm_h-1")

    _position_qc = {
        "0": "All parameters of nominal accuracy",
        "1": "Lat/lon questionable",
        "2": "Geopotential height or static pressure questionable",
        "3": "Both lat/lon and altitude/pressure questionable",
    }

    _met_qc = {
        "0": "All parameters of nominal accuracy",
        "1": "Temp/dewpoint questionable",
        "2": "FL winds questionable",
        "3": "SFMR parameters questionable",
        "4": "Temp/dewpoint and FL winds questionable",
        "5": "Temp/dewpoint SFMR questionable",
        "6": "FL winds and SFMR questionable",
        "9": "Temp/dewpoint, FL winds, and SFMR questionable",
    }

    def __init__(self, raw_hdob: str, parent_timestamp: datetime) -> None:
        # 134130 1252N 07257W 9246 00737 0061 +209 +203 061041 042 016 000 00
        self.raw_data = raw_hdob.strip().upper()

        split_data = self.raw_data.split()
        if len(split_data) != 13:
            raise HDOBDataError(
                "Invalid high density observation, expecting 13 data elements."
            )

        self.timestamp = self._get_timestamp(split_data[0], parent_timestamp)
        self.coordinates = self._get_coords(split_data[1], split_data[2])
        self.fl_pressure = self._get_fl_pressure(split_data[3])
        self.geopotential_height = self._get_geo_height(split_data[4])

        if self.fl_pressure.value is not None and self.fl_pressure.value >= 550.0:
            self.d_value = None
            self.extrap_pressure = self._get_surface_pressure(split_data[5])
        else:
            self.d_value = self._get_d_value(split_data[5])
            self.extrap_pressure = None

        self.fl_temperature = self._get_fl_temp(split_data[6])
        self.fl_dewpoint = self._get_fl_temp(split_data[7])
        if len(split_data[8]) != 6:
            raise HDOBDataError(
                f"Invalid wind data in HDOB ({split_data[8]})"
                ". Expecting 6 characters."
            )
        self.fl_wind_direction = self._get_fl_wind_dir(split_data[8][0:3])
        self.fl_wind_speed = self._get_fl_wind_speed(split_data[8][3:6])
        self.fl_wind_peak = self._get_fl_wind_peak(split_data[9])
        self.sfmr_wind_peak = self._get_sfmr_wind_peak(split_data[10])
        self.sfmr_rain_rate = self._get_sfmr_rain(split_data[11])
        if len(split_data[12]) != 2:
            raise HDOBDataError(
                f"Invalid quiality control flags in HDOB ('{split_data[12]}')."
                " Expecting 2 characters."
            )
        self.position_qc_flag = split_data[12][0]
        self.met_qc_flag = split_data[12][1]

    def __str__(self) -> str:
        return (
            f"{self.timestamp} -- {self.coordinates}, {self.fl_pressure}, "
            f"{self.geopotential_height}, {self.d_value}, {self.extrap_pressure}"
            f", {self.fl_temperature} / {self.fl_dewpoint}, "
            f"{self.fl_wind_direction} @ {self.fl_wind_speed}, {self.fl_wind_peak}"
            f", {self.sfmr_wind_peak}, {self.sfmr_rain_rate}, "
            f"{self.position_qc_flag}, {self.met_qc_flag}"
        )

    def _get_timestamp(self, time_str: str, parent_ts: datetime) -> datetime:
        if len(time_str) != 6:
            raise HDOBDataError("Invalid timestamp in HDOB, expecting 6 characters.")
        try:
            return parent_ts.replace(
                hour=int(time_str[0:2]),
                minute=int(time_str[2:4]),
                second=int(time_str[4:6]),
            )
        except ValueError as ex:
            raise HDOBDataError(
                "Invalid timestamp in HDOB. Could not convert to int."
            ) from ex

    def _get_coords(self, latitude: str, longitude: str) -> GeoPoint:

        if len(latitude) != 5 or len(longitude) != 6:
            raise HDOBDataError(
                "Invalid lat/lon in HDOB. Expecting 5 and 6 characters."
            )

        lat = float(latitude[0:2]) + (float(latitude[2:4]) / 60)
        if latitude[-1] == "S":
            lat *= -1

        long = float(longitude[0:3]) + (float(longitude[3:5]) / 60)
        if longitude[-1] == "W":
            long *= -1

        return GeoPoint(latitude=lat, longitude=long)

    def _get_fl_pressure(self, pressure: str) -> Measurement:
        if len(pressure) != 4:
            raise HDOBDataError(
                "Invalid flight level pressure in HDOB. Expecting 4 characters."
            )
        if pressure[0] == "0":
            pressure = f"1{pressure}"
        pressure = f"{pressure[0:-1]}.{pressure[-1]}"
        try:
            hpa = float(pressure)
        except ValueError as ex:
            raise HDOBDataError(
                "Invalid flight level pressure in HDOB, cannot convert to float."
            ) from ex
        return Measurement(value=hpa, unit=self._hpa_unit_info)

    def _get_geo_height(self, height: str) -> Optional[Measurement]:
        if len(height) != 5:
            raise HDOBDataError(
                "Invalid geopotential height in HDOB. Expecting 5 characters."
            )
        if "/" in height:
            return None
        try:
            geo_height = int(height)
        except ValueError as ex:
            raise HDOBDataError(
                "Invalid geopotential height in HDOB, cannot convert to int."
            ) from ex
        return Measurement(value=geo_height, unit=self._meters_unit_info)

    def _get_surface_pressure(self, data: str) -> Optional[Measurement]:
        """
        Extrapolated surface pressure or D-value (30-s average). Encoded as
        extrapolated surface pressure if aircraft static pressure is 550.0 mb or
        greater (i.e., flight altitudes at or below 550 mb). Format for
        extrapolated surface presssure is the same as for static pressure. For
        flight altitudes higher than 550 mb, XXXX is encoded by adding 5000 to
        the absolute value of the D-value. //// indicates missing value.
        """
        if len(data) != 4:
            raise HDOBDataError(
                "Invalid surface pressure in HDOB. Expecting 4 characters."
            )
        if "/" in data:
            return None

        if data[0] == "0":
            data = f"1{data}"
        data = f"{data[0:-1]}.{data[-1]}"
        try:
            hpa = float(data)
        except ValueError as ex:
            raise HDOBDataError(
                "Invalid surface pressure in HDOB, cannot convert to float."
            ) from ex

        return Measurement(value=hpa, unit=self._hpa_unit_info)

    def _get_d_value(self, data: str) -> Optional[Measurement]:
        """
        Extrapolated surface pressure or D-value (30-s average). Encoded as
        extrapolated surface pressure if aircraft static pressure is 550.0 mb or
        greater (i.e., flight altitudes at or below 550 mb). Format for
        extrapolated surface presssure is the same as for static pressure. For
        flight altitudes higher than 550 mb, XXXX is encoded by adding 5000 to
        the absolute value of the D-value. //// indicates missing value.
        """
        if len(data) != 4:
            raise HDOBDataError("Invalid D-value in HDOB. Expecting 4 characters.")
        if "/" in data:
            return None

        try:
            meters = int(data)
        except ValueError as ex:
            raise HDOBDataError(
                "Invalid surface pressure in HDOB, cannot convert to float."
            ) from ex

        return Measurement(value=meters, unit=self._meters_unit_info)

    def _get_fl_temp(self, data: str) -> Optional[Measurement]:
        """
        The air temperature or dew point in degrees and tenths Celsius, decimal
        omitted (30-s average). //// indicated missing value.
        """
        if len(data) != 4:
            raise HDOBDataError(
                "Invalid air temp/dewpoint in HDOB. Expecting 4 characters."
            )
        if "/" in data:
            return None

        try:
            with_decimal = f"{data[0:3]}.{data[-1]}"
            celsius = float(with_decimal)
        except ValueError as ex:
            raise HDOBDataError(
                "Invalid temp/dewpoint in HDOB. Cannot convert to float."
            ) from ex

        return Measurement(value=celsius, unit=self._celsius_unit_info)

    def _get_fl_wind_dir(self, data: str) -> Optional[Measurement]:
        """
        Flight-level wind direction in degrees (30-s average). North winds are
        coded as `000`. `///` indicates missing value.
        """
        if len(data) != 3:
            raise HDOBDataError(
                f"Invalid wind direction in HDOB ('{data}'). Expecting 3 characters."
            )
        if "/" in data:
            return None

        try:
            direction = int(data)
        except ValueError as ex:
            raise HDOBDataError(
                f"Invalid wind direction in HDOB ('{data}'). Cannot convert to int."
            ) from ex

        return Measurement(value=direction, unit=self._degrees_unit_info)

    def _get_fl_wind_speed(self, data: str) -> Optional[Measurement]:
        """
        Flight-level wind speed, in kt (30-s average). `///` indicates missing
        value.
        """
        if len(data) != 3:
            raise HDOBDataError(
                f"Invalid wind speed in HDOB ('{data}'). Expecting 3 characters."
            )
        if "/" in data:
            return None

        try:
            speed = int(data)
        except ValueError as ex:
            raise HDOBDataError(
                f"Invalid wind speed in HDOB ('{data}'). Cannot convert to int."
            ) from ex

        return Measurement(value=speed, unit=self._knots_unit_info)

    def _get_fl_wind_peak(self, data: str) -> Optional[Measurement]:
        """
        Peak 10-second average flight-level wind speed occuring within the
        encoding interval, in kt. `///` indicates missing value.
        """
        if len(data) != 3:
            raise HDOBDataError(
                f"Invalid peak wind in HDOB ('{data}'). Expecting 3 characters."
            )
        if "/" in data:
            return None

        try:
            speed = int(data)
        except ValueError as ex:
            raise HDOBDataError(
                f"Invalid peak wind in HDOB ('{data}'). Cannot convert to int."
            ) from ex

        return Measurement(value=speed, unit=self._knots_unit_info)

    def _get_sfmr_wind_peak(self, data: str) -> Optional[Measurement]:
        """
        Peak 10-second average surface wind speed occurring within the encoding
        interval from the Stepped Frequency Microwave Radiometer (SFMR), in kt.
        `///` indicates missing value.
        """
        if len(data) != 3:
            raise HDOBDataError(
                f"Invalid peak SFMR wind in HDOB ('{data}'). Expecting 3 characters."
            )
        if "/" in data:
            return None

        try:
            speed = int(data)
        except ValueError as ex:
            raise HDOBDataError(
                f"Invalid peak SFMR wind in HDOB ('{data}'). Cannot convert to int."
            ) from ex

        return Measurement(value=speed, unit=self._knots_unit_info)

    def _get_sfmr_rain(self, data: str) -> Optional[Measurement]:
        """
        SFMR-derived rain rate, in mm hr-1, evaluated over the 10-s interval
        chosen for the SFMR surface wind speed. `///` indicates missing value.
        """
        if len(data) != 3:
            raise HDOBDataError(
                f"Invalid SFMR rain rate in HDOB ('{data}'). Expecting 3 characters."
            )
        if "/" in data:
            return None

        try:
            rate = int(data)
        except ValueError as ex:
            raise HDOBDataError(
                f"Invalid SFMR rain rate in HDOB ('{data}'). Cannot convert to int."
            ) from ex

        return Measurement(value=rate, unit=self._mmhr_unit_info)
