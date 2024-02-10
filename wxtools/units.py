"""
Module with a static dictionary of unit information.
"""
from dataclasses import dataclass
from typing import Optional

from .errors import UnitConversionError


@dataclass(frozen=True, eq=False)
class UnitInfo:
    """
    An immutable dataclass object that holds information for a unit loosely
    based on the QUDT unit vocabulary.

    Attributes:
    * unit_kind (str) -- The type of measurement the unit is used for. Possible
    values are 'temperature', 'length', 'velocity', 'pressure', 'angle', and
    'number'.
    * label (str) -- Full name or label of the unit, ie. 'fahrenheit'.
    * symbol (str) -- The official symbol used in print, conforms to UCUM names
    when possible, ie '°F'.
    * ucum_code (Optional[str]) -- Standard UCUM symbol, if it exists. See
    https://ucum.org/ucum.html.
    * wmo_code (Optional[str]) -- Standard WMO symbol, if it exists. See
    http://codes.wmo.int/common/unit.
    * conv_factor (float) -- The factor or multiplier for conversion, if
    applicable.
    * conv_offset (float) -- The offset value for conversion, if applicable.

    Conversion factor should be 1 for base units. Note that some units (mainly
    temperature) cannot not be converted with a simple factor but also an
    offset. See link below for additional information.

    https://github.com/qudt/qudt-public-repo/tree/master/vocab/unit
    """

    unit_kind: str
    label: str
    symbol: str
    ucum_code: Optional[str]
    wmo_code: Optional[str]
    conv_factor: float
    conv_offset: float

    def __str__(self) -> str:
        return self.label.capitalize()


_ALL_UNITS: dict[str, UnitInfo] = {
    "percent": UnitInfo(
        unit_kind="number",
        label="percent",
        symbol="%",
        ucum_code=None,
        wmo_code="percent",
        conv_factor=1.0,
        conv_offset=0.0,
    ),
    "fahrenheit": UnitInfo(
        unit_kind="temperature",
        label="fahrenheit",
        symbol="°F",
        ucum_code="[degF]",
        wmo_code=None,
        conv_factor=0.5555555555555556,
        conv_offset=459.669607,
    ),
    "rankine": UnitInfo(
        unit_kind="temperature",
        label="rankine",
        symbol="°R",
        ucum_code="[degR]",
        wmo_code=None,
        conv_factor=0.5555555555555556,
        conv_offset=0.0,
    ),
    "celsius": UnitInfo(
        unit_kind="temperature",
        label="celsius",
        symbol="°C",
        ucum_code="Cel",
        wmo_code="degC",
        conv_factor=1.0,
        conv_offset=273.15,
    ),
    "kelvin": UnitInfo(
        unit_kind="temperature",
        label="kelvin",
        symbol="K",
        ucum_code="K",
        wmo_code="K",
        conv_factor=1.0,
        conv_offset=0.0,
    ),
    "foot": UnitInfo(
        unit_kind="length",
        label="foot",
        symbol="ft",
        ucum_code="[ft_i]",
        wmo_code="ft",
        conv_factor=0.3048,
        conv_offset=0.0,
    ),
    "furlong": UnitInfo(
        unit_kind="length",
        label="furlong",
        symbol="fur",
        ucum_code="[fur_us]",
        wmo_code=None,
        conv_factor=201.168,
        conv_offset=0.0,
    ),
    "fathom": UnitInfo(
        unit_kind="length",
        label="fathom",
        symbol="fath",
        ucum_code="[fth_i]",
        wmo_code=None,
        conv_factor=1.8288,
        conv_offset=0.0,
    ),
    "kilometer": UnitInfo(
        unit_kind="length",
        label="kilometer",
        symbol="km",
        ucum_code="km",
        wmo_code="km",
        conv_factor=1000.0,
        conv_offset=0.0,
    ),
    "rod": UnitInfo(
        unit_kind="length",
        label="rod",
        symbol="rd",
        ucum_code="[rd_br]",
        wmo_code=None,
        conv_factor=5.02921,
        conv_offset=0.0,
    ),
    "point": UnitInfo(
        unit_kind="length",
        label="point",
        symbol="pt",
        ucum_code="[pnt]",
        wmo_code=None,
        conv_factor=2.54e-05,
        conv_offset=0.0,
    ),
    "angstrom": UnitInfo(
        unit_kind="length",
        label="angstrom",
        symbol="Å",
        ucum_code="Ao",
        wmo_code=None,
        conv_factor=1e-10,
        conv_offset=0.0,
    ),
    "light year": UnitInfo(
        unit_kind="length",
        label="light year",
        symbol="ly",
        ucum_code="[ly]",
        wmo_code=None,
        conv_factor=9460730472580800.0,
        conv_offset=0.0,
    ),
    "chain": UnitInfo(
        unit_kind="length",
        label="chain",
        symbol="ch",
        ucum_code="[ch_br]",
        wmo_code=None,
        conv_factor=20.1168,
        conv_offset=0.0,
    ),
    "us survey foot": UnitInfo(
        unit_kind="length",
        label="us survey foot",
        symbol="ft_us",
        ucum_code="[ft_us]",
        wmo_code=None,
        conv_factor=0.3048006,
        conv_offset=0.0,
    ),
    "inch": UnitInfo(
        unit_kind="length",
        label="inch",
        symbol="in",
        ucum_code="[in_i]",
        wmo_code=None,
        conv_factor=0.0254,
        conv_offset=0.0,
    ),
    "millimeter": UnitInfo(
        unit_kind="length",
        label="millimeter",
        symbol="mm",
        ucum_code="mm",
        wmo_code="mm",
        conv_factor=0.001,
        conv_offset=0.0,
    ),
    "international mile": UnitInfo(
        unit_kind="length",
        label="international mile",
        symbol="mi",
        ucum_code="[mi_i]",
        wmo_code=None,
        conv_factor=1609.344,
        conv_offset=0.0,
    ),
    "mile us statute": UnitInfo(
        unit_kind="length",
        label="mile us statute",
        symbol="mi",
        ucum_code="[mi_us]",
        wmo_code=None,
        conv_factor=1609.347,
        conv_offset=0.0,
    ),
    "astronomical-unit": UnitInfo(
        unit_kind="length",
        label="astronomical-unit",
        symbol="AU",
        ucum_code="AU",
        wmo_code=None,
        conv_factor=149597870691.6,
        conv_offset=0.0,
    ),
    "yard": UnitInfo(
        unit_kind="length",
        label="yard",
        symbol="yd",
        ucum_code="[yd_i]",
        wmo_code=None,
        conv_factor=0.9144,
        conv_offset=0.0,
    ),
    "nautical mile": UnitInfo(
        unit_kind="length",
        label="nautical mile",
        symbol="n mile",
        ucum_code="[nmi_i]",
        wmo_code="nautical_mile",
        conv_factor=1852.0,
        conv_offset=0.0,
    ),
    "micrometer": UnitInfo(
        unit_kind="length",
        label="micrometer",
        symbol="Î¼m",
        ucum_code="um",
        wmo_code=None,
        conv_factor=1e-06,
        conv_offset=0.0,
    ),
    "meter": UnitInfo(
        unit_kind="length",
        label="meter",
        symbol="m",
        ucum_code="m",
        wmo_code="m",
        conv_factor=1.0,
        conv_offset=0.0,
    ),
    "parsec": UnitInfo(
        unit_kind="length",
        label="parsec",
        symbol="pc",
        ucum_code="pc",
        wmo_code="pc",
        conv_factor=3.085678e16,
        conv_offset=0.0,
    ),
    "fermi": UnitInfo(
        unit_kind="length",
        label="fermi",
        symbol="fm",
        ucum_code=None,
        wmo_code=None,
        conv_factor=1e-15,
        conv_offset=0.0,
    ),
    "microinch": UnitInfo(
        unit_kind="length",
        label="microinch",
        symbol="µin",
        ucum_code="u[in_i]",
        wmo_code=None,
        conv_factor=2.54e-08,
        conv_offset=0.0,
    ),
    "centimeter": UnitInfo(
        unit_kind="length",
        label="centimeter",
        symbol="cm",
        ucum_code="cm",
        wmo_code="cm",
        conv_factor=0.01,
        conv_offset=0.0,
    ),
    "femtometer": UnitInfo(
        unit_kind="length",
        label="femtometer",
        symbol="fm",
        ucum_code="fm",
        wmo_code=None,
        conv_factor=1e-15,
        conv_offset=0.0,
    ),
    "inch per second": UnitInfo(
        unit_kind="pressure",
        label="inch per second",
        symbol="in-per-sec",
        ucum_code="[in_i].s-1",
        wmo_code=None,
        conv_factor=0.0254,
        conv_offset=0.0,
    ),
    "kilometer per hour": UnitInfo(
        unit_kind="velocity",
        label="kilometer per hour",
        symbol="km/hr",
        ucum_code="km.h-1",
        wmo_code="km_h-1",
        conv_factor=0.2777777777777778,
        conv_offset=0.0,
    ),
    "meter per hour": UnitInfo(
        unit_kind="velocity",
        label="meter per hour",
        symbol="m/h",
        ucum_code="m.h-1",
        wmo_code=None,
        conv_factor=0.000277777778,
        conv_offset=0.0,
    ),
    "foot per hour": UnitInfo(
        unit_kind="velocity",
        label="foot per hour",
        symbol="ft/hr",
        ucum_code="[ft_i].h-1",
        wmo_code=None,
        conv_factor=8.466666666666667e-05,
        conv_offset=0.0,
    ),
    "meter per second": UnitInfo(
        unit_kind="velocity",
        label="meter per second",
        symbol="m/s",
        ucum_code="m.s-1",
        wmo_code=None,
        conv_factor=1.0,
        conv_offset=0.0,
    ),
    "millimeters per hour": UnitInfo(
        unit_kind="velocity",
        label="millimeters per hour",
        symbol="mm/h",
        ucum_code="mm.h-1",
        wmo_code="mm_h-1",
        conv_factor=0.0000002777778,
        conv_offset=0.0,
    ),
    "millimeters per day": UnitInfo(
        unit_kind="velocity",
        label="millimeters per day",
        symbol="mm/d",
        ucum_code="mm.d-1",
        wmo_code=None,
        conv_factor=1.15741e-08,
        conv_offset=0.0,
    ),
    "knot": UnitInfo(
        unit_kind="velocity",
        label="knot",
        symbol="kt",
        ucum_code="[kn_i]",
        wmo_code="kt",
        conv_factor=0.5144444444444445,
        conv_offset=0.0,
    ),
    "mile per minute": UnitInfo(
        unit_kind="velocity",
        label="mile per minute",
        symbol="mi/min",
        ucum_code="[mi_i].min-1",
        wmo_code=None,
        conv_factor=26.8224,
        conv_offset=0.0,
    ),
    "foot per second": UnitInfo(
        unit_kind="velocity",
        label="foot per second",
        symbol="ft/s",
        ucum_code="[ft_i].s-1",
        wmo_code=None,
        conv_factor=0.3048,
        conv_offset=0.0,
    ),
    "meter per minute": UnitInfo(
        unit_kind="velocity",
        label="meter per minute",
        symbol="m/min",
        ucum_code="m.min-1",
        wmo_code=None,
        conv_factor=0.0166666667,
        conv_offset=0.0,
    ),
    "mile per hour": UnitInfo(
        unit_kind="velocity",
        label="mile per hour",
        symbol="mi/hr",
        ucum_code="[mi_i].h-1",
        wmo_code=None,
        conv_factor=0.44704,
        conv_offset=0.0,
    ),
    "kilometer per second": UnitInfo(
        unit_kind="velocity",
        label="kilometer per second",
        symbol="km/s",
        ucum_code="km.s-1",
        wmo_code=None,
        conv_factor=1000.0,
        conv_offset=0.0,
    ),
    "foot per minute": UnitInfo(
        unit_kind="velocity",
        label="foot per minute",
        symbol="ft/min",
        ucum_code="[ft_i].min-1",
        wmo_code=None,
        conv_factor=0.00508,
        conv_offset=0.0,
    ),
    "centimeter per second": UnitInfo(
        unit_kind="velocity",
        label="centimeter per second",
        symbol="cm/s",
        ucum_code="cm.s-1",
        wmo_code=None,
        conv_factor=0.01,
        conv_offset=0.0,
    ),
    "n-per-m2": UnitInfo(
        unit_kind="pressure",
        label="n-per-m2",
        symbol="Pa",
        ucum_code="N.m-2",
        wmo_code=None,
        conv_factor=1.0,
        conv_offset=0.0,
    ),
    "inch of mercury": UnitInfo(
        unit_kind="pressure",
        label="inch of mercury",
        symbol="inHg",
        ucum_code="[in_i'Hg]",
        wmo_code=None,
        conv_factor=3386.389,
        conv_offset=0.0,
    ),
    "kip per square inch": UnitInfo(
        unit_kind="pressure",
        label="kip per square inch",
        symbol="ksi",
        ucum_code="k[lbf_av].[in_i]-2",
        wmo_code=None,
        conv_factor=6894757.89,
        conv_offset=0.0,
    ),
    "centimeter of mercury": UnitInfo(
        unit_kind="pressure",
        label="centimeter of mercury",
        symbol="cmHg",
        ucum_code="cm[Hg]",
        wmo_code=None,
        conv_factor=1333.224,
        conv_offset=0.0,
    ),
    "kilopascal": UnitInfo(
        unit_kind="pressure",
        label="kilopascal",
        symbol="kPa",
        ucum_code="kPa",
        wmo_code="kPa",
        conv_factor=1000.0,
        conv_offset=0.0,
    ),
    "torr": UnitInfo(
        unit_kind="pressure",
        label="torr",
        symbol="Torr",
        ucum_code=None,
        wmo_code=None,
        conv_factor=133.322,
        conv_offset=0.0,
    ),
    "pound force per square inch": UnitInfo(
        unit_kind="pressure",
        label="pound force per square inch",
        symbol="psia",
        ucum_code="[lbf_av].[sin_i]-1",
        wmo_code=None,
        conv_factor=6894.75789,
        conv_offset=0.0,
    ),
    "megabar": UnitInfo(
        unit_kind="pressure",
        label="megabar",
        symbol="Mbar",
        ucum_code="Mbar",
        wmo_code=None,
        conv_factor=100000000000.0,
        conv_offset=0.0,
    ),
    "bar": UnitInfo(
        unit_kind="pressure",
        label="bar",
        symbol="bar",
        ucum_code="bar",
        wmo_code=None,
        conv_factor=100000.0,
        conv_offset=0.0,
    ),
    "poundal per square foot": UnitInfo(
        unit_kind="pressure",
        label="poundal per square foot",
        symbol="pdl/ft^2",
        ucum_code="[lb_av].[ft_i].s-2.[sft_i]-1",
        wmo_code=None,
        conv_factor=1.48816443,
        conv_offset=0.0,
    ),
    "kilogram force per square centimeter": UnitInfo(
        unit_kind="pressure",
        label="kilogram force per square centimeter",
        symbol="kgf/cm^{2}",
        ucum_code="kgf.cm-2",
        wmo_code=None,
        conv_factor=98066.5,
        conv_offset=0.0,
    ),
    "millibar": UnitInfo(
        unit_kind="pressure",
        label="millibar",
        symbol="mbar",
        ucum_code="mbar",
        wmo_code=None,
        conv_factor=100.0,
        conv_offset=0.0,
    ),
    "barye": UnitInfo(
        unit_kind="pressure",
        label="barye",
        symbol="Ï",
        ucum_code=None,
        wmo_code=None,
        conv_factor=0.1,
        conv_offset=0.0,
    ),
    "hectopascal": UnitInfo(
        unit_kind="pressure",
        label="hectopascal",
        symbol="hPa",
        ucum_code="hPa",
        wmo_code="hPa",
        conv_factor=100.0,
        conv_offset=0.0,
    ),
    "decapascal": UnitInfo(
        unit_kind="pressure",
        label="decapascal",
        symbol="daPa",
        ucum_code="daPa",
        wmo_code="daPa",
        conv_factor=10.0,
        conv_offset=0.0,
    ),
    "kilobar": UnitInfo(
        unit_kind="pressure",
        label="kilobar",
        symbol="kbar",
        ucum_code="kbar",
        wmo_code=None,
        conv_factor=100000000.0,
        conv_offset=0.0,
    ),
    "pascal": UnitInfo(
        unit_kind="pressure",
        label="pascal",
        symbol="Pa",
        ucum_code="Pa",
        wmo_code="Pa",
        conv_factor=1.0,
        conv_offset=0.0,
    ),
    "kilopascal absolute": UnitInfo(
        unit_kind="pressure",
        label="kilopascal absolute",
        symbol="KPaA",
        ucum_code="kPa{absolute}",
        wmo_code=None,
        conv_factor=1.0,
        conv_offset=0.0,
    ),
    "decibar": UnitInfo(
        unit_kind="pressure",
        label="decibar",
        symbol="dbar",
        ucum_code="dbar",
        wmo_code=None,
        conv_factor=10000.0,
        conv_offset=0.0,
    ),
    "millimeter of mercury": UnitInfo(
        unit_kind="pressure",
        label="millimeter of mercury",
        symbol="mm Hg",
        ucum_code="mm[Hg]",
        wmo_code=None,
        conv_factor=133.322387415,
        conv_offset=0.0,
    ),
    "centibar": UnitInfo(
        unit_kind="pressure",
        label="centibar",
        symbol="cbar",
        ucum_code="cbar",
        wmo_code=None,
        conv_factor=1000.0,
        conv_offset=0.0,
    ),
    "psi": UnitInfo(
        unit_kind="pressure",
        label="psi",
        symbol="psi",
        ucum_code="[psi]",
        wmo_code=None,
        conv_factor=6894.75789,
        conv_offset=0.0,
    ),
    "technical atmosphere": UnitInfo(
        unit_kind="pressure",
        label="technical atmosphere",
        symbol="at",
        ucum_code="att",
        wmo_code=None,
        conv_factor=98066.5,
        conv_offset=0.0,
    ),
    "millitorr": UnitInfo(
        unit_kind="pressure",
        label="millitorr",
        symbol="mTorr",
        ucum_code=None,
        wmo_code=None,
        conv_factor=0.133322,
        conv_offset=0.0,
    ),
    "pound force per square foot": UnitInfo(
        unit_kind="pressure",
        label="pound force per square foot",
        symbol="lbf/ft^{2}",
        ucum_code="[lbf_av].[sft_i]-1",
        wmo_code=None,
        conv_factor=47.8802631,
        conv_offset=0.0,
    ),
    "inch of water": UnitInfo(
        unit_kind="pressure",
        label="inch of water",
        symbol="inAq",
        ucum_code="[in_i'H2O]",
        wmo_code=None,
        conv_factor=249.080024,
        conv_offset=0.0,
    ),
    "dyne per square centimeter": UnitInfo(
        unit_kind="pressure",
        label="dyne per square centimeter",
        symbol="dyn/cm^{2}",
        ucum_code="dyn.cm-2",
        wmo_code=None,
        conv_factor=0.1,
        conv_offset=0.0,
    ),
    "microtorr": UnitInfo(
        unit_kind="pressure",
        label="microtorr",
        symbol="Î¼Torr",
        ucum_code=None,
        wmo_code=None,
        conv_factor=0.000133322,
        conv_offset=0.0,
    ),
    "standard atmosphere": UnitInfo(
        unit_kind="pressure",
        label="standard atmosphere",
        symbol="atm",
        ucum_code="atm",
        wmo_code=None,
        conv_factor=101325.0,
        conv_offset=0.0,
    ),
    "conventional centimeter of water": UnitInfo(
        unit_kind="pressure",
        label="conventional centimeter of water",
        symbol="cmH2O",
        ucum_code="cm[H2O]",
        wmo_code=None,
        conv_factor=98.0665,
        conv_offset=0.0,
    ),
    "radian": UnitInfo(
        unit_kind="angle",
        label="radian",
        symbol="rad",
        ucum_code="rad",
        wmo_code="rad",
        conv_factor=1.0,
        conv_offset=0.0,
    ),
    "microradian": UnitInfo(
        unit_kind="angle",
        label="microradian",
        symbol="μrad",
        ucum_code="urad",
        wmo_code=None,
        conv_factor=1e-06,
        conv_offset=0.0,
    ),
    "grad": UnitInfo(
        unit_kind="angle",
        label="grad",
        symbol="grad",
        ucum_code=None,
        wmo_code=None,
        conv_factor=0.0157079633,
        conv_offset=0.0,
    ),
    "revolution": UnitInfo(
        unit_kind="angle",
        label="revolution",
        symbol="rev",
        ucum_code="{#}",
        wmo_code=None,
        conv_factor=6.28318531,
        conv_offset=0.0,
    ),
    "gon": UnitInfo(
        unit_kind="angle",
        label="gon",
        symbol="gon",
        ucum_code="gon",
        wmo_code=None,
        conv_factor=0.015707963267949,
        conv_offset=0.0,
    ),
    "degree": UnitInfo(
        unit_kind="angle",
        label="degree",
        symbol="°",
        ucum_code="deg",
        wmo_code="degree_(angle)",
        conv_factor=0.0174532925,
        conv_offset=0.0,
    ),
}

_ALL_UCUM_LABELS: dict[str, str] = {
    unit_info.ucum_code: unit_info.label
    for unit_info in _ALL_UNITS.values()
    if unit_info.ucum_code is not None
}

_ALL_WMO_LABELS: dict[str, str] = {
    unit_info.wmo_code: unit_info.label
    for unit_info in _ALL_UNITS.values()
    if unit_info.wmo_code is not None
}


def unit_by_label(label: str) -> UnitInfo:
    """
    Retrieves unit information based on the units (case insensitive) full name.

    Raises:
    * KeyError -- The unit cannot be found.

    Example:
    >>> unit_by_label('Fahrenheit')
    UnitInfo(
        unit_kind='temperature',
        label='fahrenheit',
        symbol='°F',
        ucum_code='[degF]',
        wmo_code=None,
        conv_factor=0.5555555555555556,
        conv_offset=459.669607
    )
    """
    return _ALL_UNITS[label.casefold()]


def unit_by_wmo(wmo_code: str) -> UnitInfo:
    """
    Retrieves unit information based on the units WMO code. See here for more
    details: http://codes.wmo.int/common/unit. Case sensitive.

    Raises:
    * KeyError -- The WMO label is not found.

    Example:
    >>> unit_by_wmo('degC')
    UnitInfo(
        unit_kind='temperature',
        label='celsius',
        symbol='°C',
        ucum_code='Cel',
        wmo_code='degC',
        conv_factor=1.0,
        conv_offset=273.15,
    )
    """
    label = _ALL_WMO_LABELS[wmo_code]
    return _ALL_UNITS[label]


def unit_by_ucum(ucum_code: str) -> UnitInfo:
    """
    Retrieves unit information based on the units UCUM code. See here for more
    details: https://ucum.org/ucum.html. Case sensitive.

    Raises:
    * KeyError -- The UCUM label is not found.

    Example:
    >>> unit_by_ucum('Ao')
    UnitInfo(
        unit_kind='length',
        label='angstrom',
        symbol='Å',
        ucum_code='Ao',
        wmo_code=None,
        conv_factor=1e-10,
        conv_offset=0.0,
    )
    """
    label = _ALL_UCUM_LABELS[ucum_code]
    return _ALL_UNITS[label]


def unit_by_namespace(unit_namespace: str) -> UnitInfo:
    """
    Retrieves unit information based on the units UCUM or WMO code. Case
    sensitive. The unit_namespace string should be in the format
    '{namespace}:{code}'. If no ':' is found, the entire string will be parsed
    as if it is a UCUM code.

    Raises:
    * KeyError -- The UCUM or WMO label is not found.
    * ValueError -- Cannot find a unit using the given namespace string.

    Example:
    >>> unit_by_namespace('wmoUnit:degC')
    UnitInfo(
        unit_kind='temperature',
        label='celsius',
        symbol='°C',
        ucum_code='Cel',
        wmo_code='degC',
        conv_factor=1.0,
        conv_offset=273.15,
    )
    """
    split_ns = unit_namespace.split(":")
    # (namespace, code)
    if len(split_ns) <= 1:
        return unit_by_ucum(unit_namespace)
    if split_ns[0] == "uc":
        return unit_by_ucum(split_ns[1])
    if split_ns[0] == "wmo" or split_ns[0] == "wmoUnit":
        return unit_by_wmo(split_ns[1])
    raise ValueError(f"Cannot parse namespace unit '{unit_namespace}'.")


def convert(value: float, from_unit: UnitInfo, to_unit: UnitInfo) -> float:
    """
    Converts a floating point value from one unit to another. The two units
    must be of the same kind (ie both 'temperature' or 'length').

    Raises:
    * ConversionError -- If the units are incompatible.
    """
    if from_unit.unit_kind != to_unit.unit_kind:
        raise UnitConversionError(
            f"Invalid unit types for conversion. from_unit is "
            f"'{from_unit.unit_kind}' and to_unit is '{to_unit.unit_kind}'."
        )
    if from_unit.unit_kind == "temperature":
        if from_unit.label == "fahrenheit":
            from_base = from_unit.conv_factor * (value + from_unit.conv_offset)
        else:
            from_base = from_unit.conv_factor * value + from_unit.conv_offset
        return from_base / to_unit.conv_factor - to_unit.conv_offset
    return (from_unit.conv_factor * value) / to_unit.conv_factor
