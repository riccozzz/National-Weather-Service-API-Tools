from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Optional


class NwsApiError(Exception):
    """Base exception for all NWS API errors."""


class NwsResponseError(NwsApiError):
    """Exception raised for failed NWS api requests."""


class NwsDataError(NwsApiError):
    """Exception raised for bad/corrupt/unexpected NWS data in requests."""


class UnitConversionError(Exception):
    """Exception for unit conversion errors."""


@dataclass
class ErrorDetails:
    """
    An object that holds information for a problematic JSON response.

    Attributes:
    * problem_type (str) -- A URI reference (RFC 3986) that identifies the
    problem type. This is only an identifier and is not necessarily a resolvable
    URL.
    * title (str) -- A short, human-readable summary of the problem type.
    * status (int) -- The HTTP status code (RFC 7231, Section 6) generated by
    the origin server for this occurrence of the problem.
    * detail (str) -- A human-readable explanation specific to this occurrence
    of the problem.
    * instance (str) -- A URI reference (RFC 3986) that identifies the specific
    occurrence of the problem. This is only an identifier and is not necessarily
    a resolvable URL.
    * correlation_id (str) -- A unique identifier for the request, used for NWS
    debugging purposes. Please include this identifier with any correspondence
    to help us investigate your issue.
    * parameter_errors (Optional[list[dict[str, str]]]) -- Optional extra
    information for errors caused by invalid parameters.
    """

    problem_type: str
    title: str
    status: int
    detail: str
    instance: str
    correlation_id: str
    url: str
    parameter_errors: Optional[list[dict[str, str]]] = None

    @classmethod
    def from_json(cls, jdata: dict[str, Any], url: str) -> ErrorDetails:
        """
        Constructs an ErrorDetails object using the JSON data returned from the
        National Wweather Service public API.

        Required Parameters:
        * jdata (dict[str, Any]) -- JSON response data.

        Raises:
        * KeyError -- If a required key does not exist in the dictionary.
        """
        problem_type = jdata["type"]
        if not isinstance(problem_type, str):
            raise TypeError(
                f"Expecting problem_type as string, not '{type(problem_type)}'"
            )
        title = jdata["title"]
        if not isinstance(title, str):
            raise TypeError(f"Expecting title as string, not '{type(title)}'")
        status = jdata["status"]
        if not isinstance(status, int):
            raise TypeError(f"Expecting status as int, not '{type(status)}'")
        detail = jdata["detail"]
        if not isinstance(detail, str):
            raise TypeError(f"Expecting detail as string, not '{type(detail)}'")
        instance = jdata["instance"]
        if not isinstance(instance, str):
            raise TypeError(f"Expecting instance as string, not '{type(instance)}'")
        correlation_id = jdata["correlationId"]
        if not isinstance(correlation_id, str):
            raise TypeError(
                f"Expecting correlation_id as string, not '{type(correlation_id)}'"
            )
        params = jdata.get("parameterErrors")
        if params is not None:
            if not isinstance(params, list):
                params = None
            if not all(isinstance(i, dict) for i in params):
                params = None
        return cls(
            problem_type=problem_type,
            title=title,
            status=status,
            detail=detail,
            instance=instance,
            correlation_id=correlation_id,
            url=url,
            parameter_errors=params,
        )

    def __str__(self) -> str:
        msg = f"{self.status} ({self.title})."
        if self.parameter_errors is not None:
            for perr in self.parameter_errors:
                param = perr["parameter"]
                if isinstance(param, str):
                    param = param.replace('"', "'")
                desc = perr["message"]
                if isinstance(desc, str):
                    desc = desc.replace('"', "'")
                msg = f"{msg} Parameter '{param}' is invalid. {desc}."
        msg = f"{msg} Attempted URL '{self.url}'."
        return msg
