import json
from pathlib import Path
from typing import Optional
import rdflib
import requests

"""
This module is a hack that lets me generate unit data classes from remote data.

This is pretty terrible code
"""


class UnitParseError(Exception):
    """
    Generic exception type for this module
    """

    pass


class ParseUnitsWMO:

    DEFAULT_URL = "http://codes.wmo.int/common/unit?_format=jsonld"

    def __init__(self, data: list[dict]) -> None:
        self.raw_data = data
        self.jsonld = self._filtered_json()

    @classmethod
    def fetch_data(cls, **kwargs):

        url = kwargs.get("url")
        if not isinstance(url, str):
            url = cls.DEFAULT_URL

        timeout = kwargs.get("timeout")
        if not isinstance(timeout, int):
            timeout = 5

        proxies = kwargs.get("proxies")
        if proxies is not None:
            if not isinstance(proxies, dict):
                raise TypeError("Invalid requests proxy configuration specified.")

        try:
            resp = requests.get(url=url, timeout=timeout, proxies=proxies)
            resp.raise_for_status()
            jdata: list[dict] = resp.json()["@graph"]
        except Exception as ex:
            raise UnitParseError(ex) from None

        return cls(jdata)

    def _raw_json_str(self, indent: int = None):
        return json.dumps(self.raw_data, indent=indent)

    def _json_str(self) -> str:
        jdata = self._raw_json_str()
        return jdata

    def _filtered_json(self) -> dict[str, dict]:
        json_str = self._json_str()
        json_d: list[dict] = json.loads(json_str)
        if not isinstance(json_d, list):
            raise UnitParseError("Bad raw json-ld data from source")
        if not all(isinstance(t, dict) for t in json_d):
            raise UnitParseError("Bad raw json-ld data from source")
        filtered: dict[str, dict] = UnitParse._ids_to_keys(json_d)
        filtered = UnitParse._collapse_lists(filtered)
        return filtered

    def label_from_qudt_labels(self, qudt_labels: dict[str, str]) -> Optional[str]:
        if qudt_labels is None:
            return None
        if not isinstance(self.jsonld, dict):
            return None
        folded_labels = set(s.casefold() for s in qudt_labels.values())
        for id, info in self.jsonld.items():
            if not isinstance(id, str):
                continue
            full_label = info.get("rdfs:label")
            if not isinstance(full_label, str):
                continue
            if full_label.casefold() in folded_labels:
                short_id = id.removeprefix("http://codes.wmo.int/common/unit/")
                # Celsius is a snowflake...
                if short_id == "Cel":
                    short_id = "degC"
                return short_id
        return None


class ParseUnitsQUDT:

    DEFAULT_URL = "http://qudt.org/2.1/vocab/unit"

    def __init__(self, rdf_graph: rdflib.Graph) -> None:
        self.raw_graph = rdf_graph
        self.jsonld = self._filtered_json()

    @classmethod
    def fetch_local(cls, fpath: str):
        try:
            local_file = Path(fpath).resolve()
            print(local_file)
            rdf_graph = rdflib.Graph().parse(data=local_file.read_bytes())
        except Exception as ex:
            raise UnitParseError(ex) from None
        return cls(rdf_graph)

    @classmethod
    def fetch_data(cls, **kwargs):

        url = kwargs.get("url")
        if not isinstance(url, str):
            url = cls.DEFAULT_URL

        timeout = kwargs.get("timeout")
        if not isinstance(timeout, int):
            timeout = 5

        proxies = kwargs.get("proxies")
        if proxies is not None:
            if not isinstance(proxies, dict):
                raise TypeError("Invalid requests proxy configuration specified.")

        try:
            resp = requests.get(url=url, timeout=timeout, proxies=proxies)
            resp.raise_for_status()
            rdf_graph = rdflib.Graph().parse(data=resp.text)
        except Exception as ex:
            raise UnitParseError(ex) from None

        return cls(rdf_graph)

    def get(self, key: str) -> Optional[dict]:
        return self.jsonld.get(key)

    def items(self):
        return self.jsonld.items()

    def _get_expression(self, unit_data: dict) -> Optional[str]:

        exp = unit_data.get("expression")
        # there are a few lists but who cares
        if not isinstance(exp, dict):
            return None

        value = exp.get("@value")
        if not isinstance(value, str):
            return None

        return value.replace("\\(", "").replace("\\)", "").replace("Â", "")

    def _get_udunits_code(self, unit_data: dict) -> Optional[str]:
        udu_d = unit_data.get("udunitsCode")
        if isinstance(udu_d, list):
            udu_d = udu_d[0]
        if not isinstance(udu_d, dict):
            return self._get_expression(unit_data)
        val = udu_d.get("@value")
        if not isinstance(val, str):
            return self._get_expression(unit_data)
        return val.replace("Â", "")

    def get_symbol(self, key: str) -> Optional[str]:

        unit_data = self.jsonld.get(key)
        if unit_data is None:
            return None

        symbol_d = unit_data.get("symbol")
        if isinstance(symbol_d, list):
            symbol_d = symbol_d[0]

        if not isinstance(symbol_d, dict):
            return self._get_udunits_code(unit_data)

        val = symbol_d.get("@value")

        if not isinstance(val, str):
            return self._get_udunits_code(unit_data)

        return val.replace("Â", "")

    def get_qkinds(self, key: str) -> Optional[set]:
        unit_data = self.jsonld.get(key)
        if unit_data is None:
            return None
        qkinds_d = unit_data.get("hasQuantityKind")
        qkinds = set()
        if isinstance(qkinds_d, list):
            for d in qkinds_d:
                kind = d.get("@id")
                if kind is not None:
                    qkinds.add(kind)
        elif isinstance(qkinds_d, dict):
            kind = qkinds_d.get("@id")
            if kind is not None:
                qkinds.add(kind)
        if len(qkinds) < 1:
            return None
        return qkinds

    def get_en_labels(self, key: str) -> Optional[dict[str, str]]:
        unit_data = self.jsonld.get(key)
        if unit_data is None:
            return None
        labels = {}
        label_d = unit_data.get("label")
        if isinstance(label_d, list):
            for labinfo in label_d:
                lang = labinfo.get("@language")
                if lang == "en-us" or lang == "en":
                    lab = labinfo.get("@value")
                    if isinstance(lab, str):
                        labels[lang] = lab
        elif isinstance(label_d, dict):
            lang = label_d.get("@language")
            if lang == "en-us" or lang == "en":
                lab = label_d.get("@value")
                if isinstance(lab, str):
                    labels[lang] = lab
        if len(labels) < 1:
            return None
        return labels

    def get_ucum_code(self, key: str) -> Optional[str]:
        unit_data = self.jsonld.get(key)
        if unit_data is None:
            return None
        ucum_code_d = unit_data.get("ucumCode")
        if isinstance(ucum_code_d, list):
            ucum_code_d = ucum_code_d[0]
        if not isinstance(ucum_code_d, dict):
            return None
        val = ucum_code_d.get("@value")
        if not isinstance(val, str):
            return None
        return val

    def get_conv_offset(self, key: str) -> Optional[float]:
        unit_data = self.jsonld.get(key)
        if unit_data is None:
            return None
        conv_factor_d = unit_data.get("conversionOffset")
        if not isinstance(conv_factor_d, dict):
            return None
        val = conv_factor_d.get("@value")
        if val is None:
            return None
        return float(val)

    def get_conv_factor(self, key: str) -> Optional[float]:
        unit_data = self.jsonld.get(key)
        if unit_data is None:
            return None
        conv_factor_d = unit_data.get("conversionMultiplier")
        if not isinstance(conv_factor_d, dict):
            return None
        val = conv_factor_d.get("@value")
        if val is None:
            return None
        return float(val)

    def save_json(self, filepath: str) -> None:
        fpath = Path(filepath)
        if fpath.exists():
            raise RuntimeError("File already exists")
        with fpath.open("w", encoding="utf-8") as fp:
            return json.dump(obj=self.jsonld, fp=fp, indent=4)

    def _raw_json(self):
        serialized = self.raw_graph.serialize(format="json-ld")
        return json.loads(serialized)

    def _raw_json_str(self, indent: int = None):
        return json.dumps(self._raw_json(), indent=indent)

    def _json_str(self, **kwargs) -> str:

        fold_ns = kwargs.get("fold_namespaces")
        if not isinstance(fold_ns, bool):
            fold_ns = False

        remove_ns = kwargs.get("remove_namespaces")
        if not isinstance(remove_ns, bool):
            remove_ns = False

        jdata = self._raw_json_str()

        if remove_ns:
            for ns in self.raw_graph.namespaces():
                jdata = jdata.replace(str(ns[-1]), "")
        elif fold_ns:
            for ns in self.raw_graph.namespaces():
                jdata = jdata.replace(str(ns[-1]), f"{ns[0]}:")

        return jdata

    def _filtered_json(self) -> dict[str, dict]:
        json_str = self._json_str(remove_namespaces=True)
        json_d: list[dict] = json.loads(json_str)
        if not isinstance(json_d, list):
            raise UnitParseError("Bad raw json-ld data from source")
        if not all(isinstance(t, dict) for t in json_d):
            raise UnitParseError("Bad raw json-ld data from source")
        filtered: dict[str, dict] = UnitParse._ids_to_keys(json_d)
        filtered = UnitParse._collapse_lists(filtered)
        return filtered


class UnitParse:
    def __init__(self, qudt_data, wmo_data) -> None:
        self.qudt_data: ParseUnitsQUDT = qudt_data
        self.wmo_data: ParseUnitsWMO = wmo_data

    @classmethod
    def fetch_data(cls, proxies=None):
        qudt = ParseUnitsQUDT.fetch_data(proxies=proxies)
        wmo = ParseUnitsWMO.fetch_data(proxies=proxies)
        return cls(qudt, wmo)

    def gen_and_print(self) -> None:
        units = self.generate_units()
        for k, v in units.items():
            print(k.upper())
            for s in v:
                print(f"    {s}")

    def generate_units(self) -> dict[str, list[str]]:

        units = {
            "Temperature": [],
            "Velocity": [],
            "ForcePerArea": [],  # pressure...
            "Length": [],
            "Angle": [],
        }
        my_unit_types = set(k for k in units.keys())

        for id in self.qudt_data.jsonld:

            kinds = self.qudt_data.get_qkinds(id)
            if kinds is None:
                continue

            unit_type = None
            for mu in my_unit_types:
                if mu in kinds:
                    unit_type = mu
            if unit_type is None:
                continue

            labels = self.qudt_data.get_en_labels(id)
            if not isinstance(labels, dict):
                continue
            if labels.get("en-us") is not None:
                label = labels["en-us"]
            elif labels.get("en") is not None:
                label = labels["en"]
            else:
                continue

            factor = self.qudt_data.get_conv_factor(id)
            if factor is None:
                continue

            ucum_code = self.qudt_data.get_ucum_code(id)
            wmo_code = self.wmo_data.label_from_qudt_labels(labels)
            offset = self.qudt_data.get_conv_offset(id)

            symbol = self.qudt_data.get_symbol(id)
            if symbol is None:
                continue

            if len(id) <= 5 and len(label) > 3 and len(label) < 12:
                var_name = label
            else:
                var_name = id
            var_name = var_name.strip().replace("-", "_").replace(" ", "_").upper()

            if var_name == "ANGSTROM":
                symbol = "Å"

            built_str = (
                f'{var_name} = UnitInfo(label="{label}", symbol="{symbol}", '
                f'ucum_code="{ucum_code}", wmo_code="{wmo_code}", '
                f"conv_factor={factor}, conv_offset={offset})"
            ).replace('"None"', "None")

            units[unit_type].append(built_str)

        return units

    @staticmethod
    def _ids_to_keys(data: list[dict]) -> dict[str, dict]:
        kvdata: dict[str, dict] = {}
        for section in data:
            id = section.pop("@id")
            if not isinstance(id, str):
                raise KeyError("No id in section, possibly bad data.")
            else:
                kvdata[id.split("/")[-1]] = section
        return kvdata

    @staticmethod
    def _collapse_lists(data: dict[str, dict]) -> dict[str, dict]:
        new_data = {}
        for head_key, head_dict in data.items():
            subdict = {}
            for k, v in head_dict.items():
                if isinstance(v, list):
                    if len(v) == 1:
                        subdict[k] = v[0]
                    elif len(v) == 0:
                        subdict[k] = None
                    else:
                        subdict[k] = v
                else:
                    subdict[k] = v
                new_data[head_key] = subdict
        return new_data
