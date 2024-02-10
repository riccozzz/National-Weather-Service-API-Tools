"""
Low level methods for retrieving data from the National Weather Service public
API using the requests library. Every method will have **params keyword args for
intermediary API changes, and in some cases there are simply too many optional
args to include them,

https://www.weather.gov/documentation/services-web-api
"""
from collections.abc import Iterable, Collection
from datetime import datetime
from typing import Any, Optional, Union
import requests
from requests.utils import requote_uri
from .errors import ErrorDetails, NwsDataError, NwsResponseError


def _create_param_str(**params: Any) -> str:
    """
    Helper method. Turns human readable API parameters into a single string to be
    appended to an endpoint URI. If params is empty, an empty string is returned.

    >>> _create_param_str(state=('CT', 'MA'), active=False, search='hello world')
    'state=CT,MA&active=False&search=hello%20world'
    """

    unparsed = ""
    for k, v in params.items():
        if isinstance(v, bool):
            if v:
                unparsed = f"{unparsed}&{k}=true"
            else:
                unparsed = f"{unparsed}&{k}=false"
        elif not isinstance(v, str) and isinstance(v, Collection):
            unparsed = f"{unparsed}&{k}={','.join(v)}"
        else:
            unparsed = f"{unparsed}&{k}={v}"
    unparsed = unparsed.removeprefix("&")
    if len(unparsed) < 2:
        return ""
    parsed = requote_uri(unparsed)
    if isinstance(parsed, str):
        return parsed
    return ""


def _create_url(endpoint: str, **params: Any) -> str:
    """Helper method. Returns a NWS URL with a given endpoint and arguments."""
    nws_url = "https://api.weather.gov"
    if not endpoint.startswith("/"):
        full_url = f"{nws_url}/{endpoint}"
    else:
        full_url = f"{nws_url}{endpoint}"
    if len(params) > 0:
        param_str = _create_param_str(**params)
        full_url = f"{full_url}?{param_str}"
    return full_url


def _glossary_convert(raw_gloss: Iterable[Any]) -> dict[str, str]:
    """
    Helper method that converts the glossary data into a more manageable
    dictionary in form: `{'term': 'definition'}`.
    """
    glossdict: dict[str, str] = {}
    for item in raw_gloss:
        if isinstance(item, dict):
            term = item.get("term")
            definition = item.get("definition")
            if isinstance(term, str) and isinstance(definition, str):
                term = term.casefold()
                glossdict[term.casefold()] = definition
    return glossdict


def _create_headers(feature_flags: Optional[Collection[str]] = None) -> dict[str, str]:
    headers = {
        "Accept": "application/ld+json",
        "Content-Type": "application/ld+json",
    }
    if feature_flags is not None:
        headers["Feature-Flags"] = ",".join(i.strip() for i in feature_flags)
    return headers


def _get_proxies(proxies: Optional[Any]) -> Optional[dict[str, str]]:
    if not isinstance(proxies, dict):
        return None
    return proxies


def _get_timeout(timeout: Optional[Any]) -> int:
    if isinstance(timeout, int):
        return timeout
    if isinstance(timeout, (float, str)):
        return int(timeout)
    return 10


def _get_feature_flags(flags: Optional[Any]) -> Optional[Collection[str]]:
    if not isinstance(flags, Collection):
        return None
    if len(flags) == 0:
        return None
    if not all(isinstance(i, str) for i in flags):
        return None
    return flags


def get(endpoint: str, **params: Any) -> requests.Response:
    """
    Retrieves remote NWS JSON-LD data with the given endpoint and arguments.
    """
    feature_flags = _get_feature_flags(params.pop("feature_flags", None))
    proxies = _get_proxies(params.pop("proxies", None))
    timeout = _get_timeout(params.pop("timeout", None))
    full_url = _create_url(endpoint, **params)
    headers = _create_headers(feature_flags)
    try:
        resp = requests.get(
            url=full_url,
            timeout=timeout,
            proxies=proxies,
            headers=headers,
        )
        if resp.status_code >= 400:
            jdata = resp.json()
            if isinstance(jdata, dict):
                error = ErrorDetails.from_json(jdata, full_url)
                raise NwsResponseError(error)
        resp.raise_for_status()
        return resp
    except requests.RequestException as ex:
        raise NwsResponseError(ex) from None


def get_json(endpoint: str, **params: Any) -> dict[str, Any]:
    """
    Retrieves remote NWS data with the given endpoint and arguments as json.
    """
    resp = get(endpoint, **params)
    jdata = resp.json()
    if not isinstance(jdata, dict):
        raise NwsDataError(
            f"Expecting response data as typed 'dict', not type '{type(jdata)}'"
        )
    if not all(isinstance(k, str) for k in jdata):
        raise NwsDataError("Expecting all response dictionary keys as strings")
    return jdata


def alerts(**params: Any) -> dict[str, Any]:
    """
    Retrieves all alerts from the National Weather Service public API. Endpoint
    reference '/alerts'. Use active_alerts() for only currently active alerts.

    Optional Parameters:
    * start (str) -- Start time of alert.
    * end (str) -- End time of alert.
    * status (Union[str, Collection[str]]) -- Status ('actual', 'exercise',
    'system', 'test', 'draft').
    * message_type (Union[str, Collection[str]]) -- Message type ('alert',
    'update', 'cancel').
    * event (Union[str, Collection[str]]) -- Event name.
    * code (Union[str, Collection[str]]) -- Event code.
    * area (Union[str, Collection[str]]) -- State/territory code or marine area
    code. This parameter is incompatible with the following parameters: point,
    region, region_type, zone.
    * point (str) -- Point ('latitude, longitude'). This parameter is incompatible
    with the following parameters: area, region, region_type, zone.
    * region (Union[str, Collection[str]]) -- Marine region code ('AL', 'AT',
    'GL', 'GM', 'PA', 'PI'). This parameter is incompatible with the following
    parameters: area, point, region_type, zone.
    * region_type (str) -- Region type ('land' or 'marine'). This parameter is
    incompatible with the following parameters: area, point, region, zone.
    * zone (Union[str, Collection[str]]) -- Zone ID (forecast or county). This
    parameter is incompatible with the following parameters: area, point,
    region, region_type
    * urgency (Union[str, Collection[str]]) -- Urgency ('Immediate', 'Expected',
    'Future', 'Past', 'Unknown')
    * severity (Union[str, Collection[str]]) -- Severity ('Extreme', 'Severe',
    'Moderate', 'Minor', 'Unknown')
    * certainty (Union[str, Collection[str]]) -- Certainty ('Observed',
    'Likely', 'Possible', 'Unlikely', 'Unknown')
    * limit (int) -- Limit number of alerts in response.
    * cursor (str) -- Pagination cursor.
    """
    return get_json("/alerts", **params)


def active_alerts(**params: Any) -> dict[str, Any]:
    """
    Retrieves all currently active alerts from the National Weather Service
    public API. Endpoint reference '/alerts/active'.

    Optional Parameters:
    * status (Union[str, Collection[str]]) -- Status ('actual', 'exercise',
    'system', 'test', 'draft').
    * message_type (Union[str, Collection[str]]) -- Message type ('alert',
    'update', 'cancel').
    * event (Union[str, Collection[str]]) -- Event name.
    * code (Union[str, Collection[str]]) -- Event code.
    * area (Union[str, Collection[str]]) -- State/territory code or marine area
    code. This parameter is incompatible with the following parameters: point,
    region, region_type, zone.
    * point (str) -- Point ('latitude, longitude'). This parameter is incompatible
    with the following parameters: area, region, region_type, zone.
    * region (Union[str, Collection[str]]) -- Marine region code ('AL', 'AT',
    'GL', 'GM', 'PA', 'PI'). This parameter is incompatible with the following
    parameters: area, point, region_type, zone.
    * region_type (str) -- Region type ('land' or 'marine'). This parameter is
    incompatible with the following parameters: area, point, region, zone.
    * zone (Union[str, Collection[str]]) -- Zone ID (forecast or county). This
    parameter is incompatible with the following parameters: area, point,
    region, region_type
    * urgency (Union[str, Collection[str]]) -- Urgency ('Immediate', 'Expected',
    'Future', 'Past', 'Unknown')
    * severity (Union[str, Collection[str]]) -- Severity ('Extreme', 'Severe',
    'Moderate', 'Minor', 'Unknown')
    * certainty (Union[str, Collection[str]]) -- Certainty ('Observed',
    'Likely', 'Possible', 'Unlikely', 'Unknown')
    * limit (int) -- Limit number of alerts in response.
    """
    return get_json("/alerts/active", **params)


def active_alert_count(**params: Any) -> dict[str, Any]:
    """
    Retrieves information on the number of active alerts. Endpoint reference
    '/alerts/active/count'.
    """
    return get_json("/alerts/active/count", **params)


def active_alerts_zone(zone_id: str, **params: Any) -> dict[str, Any]:
    """
    Retrieves active alerts for the given NWS public zone or county from the
    National Weather Service public API. Endpoint reference
    '/alerts/active/zone/{zoneId}'.

    Required Parameters:
    * zone_id (str) -- NWS public zone/county identifier.
    """
    return get_json(f"/alerts/active/zone/{zone_id}", **params)


def active_alerts_area(area: str, **params: Any) -> dict[str, Any]:
    """
    Retrieves active alerts for the given area (state or marine area) from the
    National Weather Service public API. Endpoint reference
    '/alerts/active/area/{area}'.

    Required Parameters:
    * area (str) -- NWS public zone/county identifier.
    """
    return get_json(f"/alerts/active/area/{area}", **params)


def active_alerts_region(region: str, **params: Any) -> dict[str, Any]:
    """
    Retrieves active alerts for the given marine region from the National
    Weather Service public API. Endpoint reference
    '/alerts/active/region/{region}'.

    Required Parameters:
    * region (str) -- Marine region ID ('AL', 'AT', 'GL', 'GM', 'PA', 'PI').
    """
    return get_json(f"/alerts/active/region/{region}", **params)


def alert_types(**params: Any) -> dict[str, Any]:
    """
    Retrieves a collection of recognized alert event types from the National
    Weather Service public API. Endpoint reference '/alerts/types'.
    """
    return get_json("/alerts/types", **params)


def alert(alert_id: str, **params: Any) -> dict[str, Any]:
    """
    Retrieves a single alert from the National Weather Service public API using
    an identifier. Endpoint reference '/alerts/{id}'.

    Required Parameters:
    * alert_id (str) -- The identifier of the alert record.
    """
    return get_json(f"/alerts/{alert_id}", **params)


def glossary(**params: Any) -> dict[str, str]:
    """
    NWS API glossary terms, as a dictionary in form: `{'term': 'definition'}`.
    Endpoint reference '/glossary'.

    Notes:
    * The definitions may contain HTML tags as well as newlines.
    * Keys are casefolded via casefold(), users should do the same for lookups.
    * The resulting dictionary may be sevral hundred kilobytes of data.

    >>> glossary()['AAAS']
    'American Association for the Advancement of Science'

    https://api.weather.gov/glossary
    """
    jdata = get_json("/glossary", **params)
    gloss = jdata.get("glossary")
    if not isinstance(gloss, Iterable):
        raise NwsDataError("Invalid glossary data, not iterable.")
    return _glossary_convert(gloss)


def gridpoints(wfo: str, x: int, y: int, **params: Any) -> dict[str, Any]:
    """
    Returns raw numerical forecast data for a 2.5km grid area from the National
    Weather Service public API. Endpoint reference '/gridpoints/{wfo}/{x},{y}'.
    To retrieve grid points for a particular area, use `points()` first.

    Required Parameters:
    * wfo (str) -- Forecast office ID.
    * x (int) -- Forecast grid X coordinate.
    * y (int) -- Forecast grid Y coordinate.

    See API documentation for schema `NWSForecastOfficeId` for full list of
    possible forecast office IDs.

    https://www.weather.gov/documentation/services-web-api#/
    """
    return get_json(f"/gridpoints/{wfo}/{x},{y}", **params)


def gridpoints_forecast(wfo: str, x: int, y: int, **params: Any) -> dict[str, Any]:
    """
    Returns a textual forecast for a 2.5km grid area from the National Weather
    Service public API. Endpoint reference '/gridpoints/{wfo}/{x},{y}/forecast'.
    To retrieve grid points for a particular area, use `points()` first.

    Required Parameters:
    * wfo (str) -- Forecast office ID.
    * x (int) -- Forecast grid X coordinate.
    * y (int) -- Forecast grid Y coordinate.

    Optional Parameters:
    * units (str) -- Use US customary or SI (metric) units in textual output
    ('us', 'si').
    * feature_flags (Iterable[str]) -- List of future and experimental features
    (see documentation for more info) to enable.

    See API documentation for schema `NWSForecastOfficeId` for full list of
    possible forecast office IDs.

    https://www.weather.gov/documentation/services-web-api#/
    """
    return get_json(f"/gridpoints/{wfo}/{x},{y}/forecast", **params)


def gridpoints_forecast_hourly(
    wfo: str,
    x: int,
    y: int,
    units: Optional[str] = None,
    **params: Any,
) -> dict[str, Any]:
    """
    Returns a textual hourly forecast for a 2.5km grid area from the National
    Weather Service public API. Endpoint reference
    '/gridpoints/{wfo}/{x},{y}/forecast/hourly'. To retrieve grid points for a
    particular area, use `points()` first.

    Required Parameters:
    * wfo (str) -- Forecast office ID.
    * x (int) -- Forecast grid X coordinate.
    * y (int) -- Forecast grid Y coordinate.

    Optional Parameters:
    * units (str) -- Use US customary or SI (metric) units in textual output
    ('us', 'si').
    * feature_flags (Iterable[str]) -- List of future and experimental features
    (see documentation for more info) to enable.

    See API documentation for schema `NWSForecastOfficeId` for full list of
    possible forecast office IDs.

    https://www.weather.gov/documentation/services-web-api#/
    """
    if units is not None:
        params["units"] = units
    return get_json(f"/gridpoints/{wfo}/{x},{y}/forecast/hourly", **params)


def gridpoints_stations(wfo: str, x: int, y: int, **params: Any) -> dict[str, Any]:
    """
    Returns a list of observation stations usable for a given 2.5km grid area
    from the National Weather Service public API. Endpoint reference
    '/gridpoints/{wfo}/{x},{y}/stations'. To retrieve grid points for a
    particular area, use `points()` first.

    Required Parameters:
    * wfo (str) -- Forecast office ID.
    * x (int) -- Forecast grid X coordinate.
    * y (int) -- Forecast grid Y coordinate.

    See API documentation for schema `NWSForecastOfficeId` for full list of
    possible forecast office IDs.

    https://www.weather.gov/documentation/services-web-api#/
    """
    return get_json(f"/gridpoints/{wfo}/{x},{y}/stations", **params)


def station_observations(
    station_id: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: Optional[int] = None,
    **params: Any,
) -> dict[str, Any]:
    """
    Retrieves a collection of observations for a given station from the National
    Weather Service public API. Endpoint reference
    '/stations/{stationId}/observations'.

    Required Parameters:
    * station_id (str) -- Observation station ID.

    Optional Parameters:
    * start (str) -- Start time.
    * end (str) -- End time.
    * limit (int) -- Limit the amount of observations returned.
    """
    if start is not None:
        params["start"] = start
    if end is not None:
        params["end"] = end
    if limit is not None:
        params["limit"] = limit
    return get_json(f"/stations/{station_id}/observations", **params)


def station_observations_latest(
    station_id: str, require_qc: Optional[bool] = None, **params: Any
) -> dict[str, Any]:
    """
    Retrieves the latest observations for a given station from the National
    Weather Service public API. Endpoint reference
    '/stations/{stationId}/observations/latest'.

    Required Parameters:
    * station_id (str) -- Observation station ID.

    Optional Parameters:
    * require_qc (bool) -- Require quality control.
    """
    if require_qc is not None:
        params["require_qc"] = require_qc
    return get_json(f"/stations/{station_id}/observations/latest", **params)


def station_observations_time(
    station_id: str,
    time: Union[str, datetime],
    require_qc: Optional[bool] = None,
    **params: Any,
) -> dict[str, Any]:
    """
    Retrieves a single observations for a given station from the National
    Weather Service public API. Endpoint reference
    '/stations/{stationId}/observations/{time}'.

    Required Parameters:
    * station_id (str) -- Observation station ID.
    * time (str | datetime) -- Timestamp of requested observation in ISO format.

    Optional Parameters:
    * require_qc (bool) -- Require quality control.
    """
    if isinstance(time, datetime):
        ts = time.isoformat(sep="T")
        return get_json(f"/stations/{station_id}/observations/{ts}", **params)
    if require_qc is not None:
        params["require_qc"] = require_qc
    return get_json(f"/stations/{station_id}/observations/{time}", **params)


def stations(
    station_id: Optional[Collection[str]] = None,
    state: Optional[Collection[str]] = None,
    limit: Optional[int] = None,
    cursor: Optional[str] = None,
    **params: Any,
) -> dict[str, Any]:
    """
    Retrieves a collection of observations stations from the National
    Weather Service public API. Endpoint reference '/stations'.

    Optional Parameters:
    * station_id (Collection[str]) -- Filter by observation station IDs.
    * state (Collection[str]) -- Filter by state/marine area codes.
    * limit (int) -- Limit number of stations in resposne.
    * cursor (str) -- Pagination cursor (in case of >500 results)
    """
    if station_id is not None:
        params["id"] = station_id
    if state is not None:
        params["state"] = state
    if limit is not None:
        params["limit"] = limit
    if cursor is not None:
        params["cursor"] = cursor
    return get_json("/stations", **params)


def stations_id(station_id: str, **params: Any) -> dict[str, Any]:
    """
    Retrieves metadata about a given observation station from the National
    Weather Service public API. Endpoint reference '/stations/{stationId}'.

    Required Parameters:
    * station_id (str) -- Observation station ID.
    """
    return get_json(f"/stations/{station_id}", **params)


def office(office_id: str, **params: Any) -> dict[str, Any]:
    """
    Retrieves mmetadata about a NWS forecast office from the National Weather
    Service public API. Endpoint reference '/offices/{officeId}'.

    See API documentation for schema `NWSForecastOfficeId` for full list of
    possible forecast office IDs.

    https://www.weather.gov/documentation/services-web-api#/

    Required Parameters:
    * office_id (str) -- NWS forecast office ID.
    """
    return get_json(f"/offices/{office_id}", **params)


def office_headline_id(
    office_id: str, headline_id: str, **params: Any
) -> dict[str, Any]:
    """
    Retrieves a specific news headline for a given NWS office from the National
    Weather Service public API. Endpoint reference
    '/offices/{officeId}/headlines/{headlineId}'.

    See API documentation for schema `NWSForecastOfficeId` for full list of
    possible forecast office IDs.

    https://www.weather.gov/documentation/services-web-api#/

    Required Parameters:
    * office_id (str) -- NWS forecast office ID.
    * headline_id (str) -- Headline record ID.
    """
    return get_json(f"/offices/{office_id}/headlines/{headline_id}", **params)


def office_headlines(office_id: str, **params: Any) -> dict[str, Any]:
    """
    Retrieves a list of news headlines for a given NWS office from the National
    Weather Service public API. Endpoint reference
    '/offices/{officeId}/headlines'.

    See API documentation for schema `NWSForecastOfficeId` for full list of
    possible forecast office IDs.

    https://www.weather.gov/documentation/services-web-api#/

    Required Parameters:
    * office_id (str) -- NWS forecast office ID.
    """
    return get_json(f"/offices/{office_id}/headlines", **params)


def points(point_str: str, **params: Any) -> dict[str, Any]:
    """
    Retrieves metadata about a given latitude/longitude point from the National
    Weather Service public API. Endpoint reference '/points/{point}'.

    Required Parameters:
    * point_str (str) -- Location point in format '{latitude},{longitude}'.
    """
    return get_json(f"/points/{point_str}", **params)


def radar_servers(
    reporting_host: Optional[str] = None, **params: Any
) -> dict[str, Any]:
    """
    Retrieves a list of radar servers from the National Weather Service public
    API. Endpoint reference '/radar/servers'.

    Optional Parameters:
    * reporting_host (str) -- Show records from specific reporting host.
    """
    if reporting_host is not None:
        params["reportingHost"] = reporting_host
    return get_json("/radar/servers", **params)


def radar_servers_id(
    server_id: str, reporting_host: Optional[str] = None, **params: Any
) -> dict[str, Any]:
    """
    Retrieves metadata about a given radar server from the National Weather
    Service public API. Endpoint reference '/radar/servers/{id}'.

    Required Parameters:
    * server_id (str) -- Server ID.

    Optional Parameters:
    * reporting_host (str) -- Show records from specific reporting host.
    """
    if reporting_host is not None:
        params["reportingHost"] = reporting_host
    return get_json(f"/radar/servers/{server_id}", **params)


def radar_stations(
    station_type: Optional[Collection[str]] = None,
    reporting_host: Optional[str] = None,
    host: Optional[str] = None,
    **params: Any,
) -> dict[str, Any]:
    """
    Retrieves a list of radar stations from the National Weather
    Service public API. Endpoint reference '/radar/stations'.

    Optional Parameters:
    * station_type (Collection[str]) -- Limit results to a specific station type
    or types.
    * reporting_host (str) -- Show records from specific reporting host.
    * host (str) -- Show latency info from specific LDM host.
    """
    if station_type is not None:
        params["stationType"] = station_type
    if reporting_host is not None:
        params["reportingHost"] = reporting_host
    if host is not None:
        params["host"] = host
    return get_json("/radar/stations", **params)


def radar_station_id(
    station_id: str,
    reporting_host: Optional[str] = None,
    host: Optional[str] = None,
    **params: Any,
) -> dict[str, Any]:
    """
    Retrieves metadata about a given radar station from the National Weather
    Service public API. Endpoint reference '/radar/stations/{stationId}'.

    Required Parameters:
    * station_id (str) -- Radar station ID.

    Optional Parameters:
    * reporting_host (str) -- Show RDA and latency info from specific reporting
    host
    * host (str) -- Show latency info from specific LDM host.
    """
    if reporting_host is not None:
        params["reportingHost"] = reporting_host
    if host is not None:
        params["host"] = host
    return get_json(f"/radar/stations/{station_id}", **params)


def radar_station_id_alarms(station_id: str, **params: Any) -> dict[str, Any]:
    """
    Retrieves metadata about a given radar station alarms from the National Weather
    Service public API. Endpoint reference '/radar/stations/{stationId}/alarms'.

    Required Parameters:
    * station_id (str) -- Radar station ID.
    """
    return get_json(f"/radar/stations/{station_id}/alarms", **params)


def radar_queues_host(host: str, **params: Any) -> dict[str, Any]:
    """
    Retrieves metadata about a given radar queue from the National Weather
    Service public API. Endpoint reference '/radar/queues/{host}'.

    For the time ranges specified in optional parameters, this is a time
    interval in ISO 8601 format. This can be one of:
    1. Start and end time
    2. Start time and duration
    3. Duration and end time

    Examples:
    * '2007-03-01T13:00:00Z/2008-05-11T15:30:00Z'
    * '2007-03-01T13:00:00Z/P1Y2M10DT2H30M'
    * 'P1Y2M10DT2H30M/2008-05-11T15:30:00Z'

    Required Parameters:
    * host (str) -- LDM host.

    Optional Parameters:
    * limit (int) -- Record limit, between 1 and 500.
    * arrived (str) -- Range for arrival time.
    * created (str) -- Range for creation time.
    * published (str) -- Range for publish time.
    * station (str) -- Station identifier.
    * type (str) -- Record type.
    * feed (str) -- Originating product feed.
    * resolution (str) -- Resolution version.
    """
    return get_json(f"/radar/queues/{host}", **params)


def radar_profilers_id(
    station_id: str,
    time: Optional[str] = None,
    interval: Optional[str] = None,
    **params: Any,
) -> dict[str, Any]:
    """
    Retrieves metadata about a given radar wind profiler from the National Weather
    Service public API. Endpoint reference '/radar/queues/{host}'.

    For the time ranges specified in optional parameters, this is a time
    interval in ISO 8601 format. This can be one of:
    1. Start and end time
    2. Start time and duration
    3. Duration and end time

    Examples:
    * '2007-03-01T13:00:00Z/2008-05-11T15:30:00Z'
    * '2007-03-01T13:00:00Z/P1Y2M10DT2H30M'
    * 'P1Y2M10DT2H30M/2008-05-11T15:30:00Z'

    Required Parameters:
    * station_id (str) -- Profiler station ID.

    Optional Parameters:
    * time (str) -- Time interval.
    * interval (str) -- Averaging interval.
    """
    if time is not None:
        params["time"] = time
    if interval is not None:
        params["interval"] = interval
    return get_json(f"/radar/profilers/{station_id}", **params)


def products(**params: Any) -> dict[str, Any]:
    """
    Retrieves a list of text products from the National Weather Service public
    API. Endpoint reference '/products'.

    Optional Parameters:
    * location (Collection[str]) -- Location IDs.
    * start (str) -- Start time.
    * end (str) -- End time.
    * office (Collection[str]) -- Issuing office.
    * wmoid (Collection[str]) -- WMO id code.
    * type (Collection[str]) -- Product code.
    * limit (int) -- Limit number of products in response.
    """
    return get_json("/products", **params)


def products_locations(**params: Any) -> dict[str, Any]:
    """
    Retrieves a list of valid text product issuance locations from the National
    Weather Service public API. Endpoint reference '/products/locations'.
    """
    return get_json("/products/locations", **params)


def products_types(**params: Any) -> dict[str, Any]:
    """
    Retrieves a list of valid text product types and codes from the National
    Weather Service public API. Endpoint reference '/products/types'.
    """
    return get_json("/products/types", **params)


def products_id(product_id: str, **params: Any) -> dict[str, Any]:
    """
    Retrieves a specific text product from the National Weather Service public
    API. Endpoint reference '/products/{productId}'.

    Required Parameters:
    * product_id (str)
    """
    return get_json(f"/products/{product_id}", **params)


def products_type_id(type_id: str, **params: Any) -> dict[str, Any]:
    """
    Retrieves a list of text products of a given type from the National Weather
    Service public API. Endpoint reference '/products/types/{typeId}'.

    Required Parameters:
    * type_id (str)
    """
    return get_json(f"/products/types/{type_id}", **params)


def products_type_id_locations(type_id: str, **params: Any) -> dict[str, Any]:
    """
    Retrieves a list of valid text product issuance locations for a given
    product type from the National Weather Service public API. Endpoint
    reference '/products/types/{typeId}/locations'.

    Required Parameters:
    * type_id (str)
    """
    return get_json(f"/products/types/{type_id}/locations", **params)


def products_locations_id_types(location_id: str, **params: Any) -> dict[str, Any]:
    """
    Retrieves a list of valid text product types for a given issuance location
    from the National Weather Service public API. Endpoint reference
    '/products/locations/{locationId}/types'.

    Required Parameters:
    * location_id (str)
    """
    return get_json(f"/products/locations/{location_id}/types", **params)


def products_types_id_locations_id(
    type_id: str, location_id: str, **params: Any
) -> dict[str, Any]:
    """
    Retrieves a list of text products of a given type for a given issuance
    location from the National Weather Service public API. Endpoint reference
    '/products/types/{typeId}/locations/{locationId}'.

    Required Parameters:
    * type_id (str)
    * location_id (str)
    """
    return get_json(f"/products/types/{type_id}/locations/{location_id}", **params)


def zones(**params: Any) -> dict[str, Any]:
    """
    Retrieves a list of zones from the National Weather Service public API.
    Endpoint reference '/zones'.

    Optional Parameters:
    * zone_id (Collection[str]) -- Zone IDs (forecast or county).
    * area (Collection[str]) -- State/marine area code.
    * region (Collection[str]) -- Region code.
    * type (Collection[str]) -- Zone type ['land', 'marine', 'forecast',
    'public', 'coastal', 'offshore', 'fire', 'county'].
    * point (str) -- Point (latitude,longitude).
    * include_geometry (bool) -- Include geometry in results.
    * limit (int) -- Limit number of zones in results.
    * effective (str) -- Effective date/time.
    """
    if "zone_id" in params:
        params["id"] = params.pop("zone_id")
    return get_json("/zones", **params)


def zones_type(zone_type: str, **params: Any) -> dict[str, Any]:
    """
    Retrieves a list of zones of a give type from the National Weather Service
    public API. Endpoint reference '/zones/{type}'.

    Required Parameters:
    * zone_type (str) -- Zone type ['land', 'marine', 'forecast', 'public',
    'coastal', 'offshore', 'fire', 'county'].

    Optional Parameters:
    * zone_id (Collection[str]) -- Zone IDs (forecast or county).
    * area (Collection[str]) -- State/marine area code.
    * region (Collection[str]) -- Region code.
    * point (str) -- Point (latitude,longitude).
    * include_geometry (bool) -- Include geometry in results.
    * limit (int) -- Limit number of zones in results.
    * effective (str) -- Effective date/time.
    """
    if "zone_id" in params:
        params["id"] = params.pop("zone_id")
    return get_json(f"/zones/{zone_type}", **params)


def zones_type_id(
    zone_type: str, zone_id: str, effective: Optional[str] = None, **params: Any
) -> dict[str, Any]:
    """
    Retrieves metadata about a given zone from the National Weather Service
    public API. Endpoint reference '/zones/{type}/{zoneId}'.

    Required Parameters:
    * zone_type (str) -- Zone type ['forecast', 'fire', 'county'].
    * zone_id (str) -- NWS public zone/county identifier.

    Optional Parameters:
    * effective (str) -- Effective date/time.
    """
    if effective is not None:
        params["effective"] = effective
    return get_json(f"/zones/{zone_type}/{zone_id}", **params)


def zones_type_id_forecast(
    zone_type: str, zone_id: str, **params: Any
) -> dict[str, Any]:
    """
    Retrieves the current zone forecast for a given zone from the National
    Weather Service public API. Endpoint reference
    '/zones/{type}/{zoneId}/forecast'.

    Required Parameters:
    * zone_type (str) -- Zone type ['forecast', 'fire', 'county'].
    * zone_id (str) -- NWS public zone/county identifier.
    """
    return get_json(f"/zones/{zone_type}/{zone_id}/forecast", **params)


def zones_forecast_id_observations(
    zone_id: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: Optional[int] = None,
    **params: Any,
) -> dict[str, Any]:
    """
    Retrievesa list of observations for a given zone from the National Weather
    Service public API. Endpoint reference
    '/zones/forecast/{zoneId}/observations'.

    Required Parameters:
    * zone_id (str) -- NWS public zone/county identifier.

    Optional Parameters:
    * start (str) -- Start date/time.
    * end (str) -- End date/time.
    * limit (int) -- Limit number of responses.
    """
    if start is not None:
        params["start"] = start
    if end is not None:
        params["end"] = end
    if limit is not None:
        params["limit"] = limit
    return get_json(f"/zones/forecast/{zone_id}/observations", **params)


def zones_forecast_id_stations(
    zone_id: str,
    **params: Any,
) -> dict[str, Any]:
    """
    Retrieves a list of observation stations for a given zone from the National
    Weather Service public API. Endpoint reference
    '/zones/forecast/{zoneId}/stations'.

    Required Parameters:
    * zone_id (str) -- NWS public zone/county identifier.
    """
    return get_json(f"/zones/forecast/{zone_id}/stations", **params)
