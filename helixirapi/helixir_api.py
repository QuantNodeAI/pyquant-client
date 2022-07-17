"""
Rest API client library for Helixir data source.
"""

from typing import List, Dict, Union, Tuple, Type
import sys
import warnings


if sys.version_info >= (3, 8): # TODO: is it necessary?
    from typing import Literal #python >=3.8
else:
    from typing_extensions import Literal
import time
from datetime import datetime as dt
from dateutil.parser import isoparse

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from tqdm.auto import tqdm, trange
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from helixirapi import models
from helixirapi.models import unmarshal

Timeframes = Literal["M1", "M5", "M10", "M15", "M30", "H1", "H4", "H12", "D1", "W1", "MN1"]


class HelixirApi:
    """
    Main rest API client library class.

    Attributes
    ----------
    auth_token: str
        Token form authentication.
    
    headers: Dict[str, str]
        Headers for requests.
    """

    DEFAULT_API_SERVER = "https://api.helixir.io/"
    API_VERSION = "v1"

    DATA_EPOCH = dt.fromisoformat("2021-04-12T13:45:00+02:00")
    AGAINSTS = [None, "USD", "PEG"]
    SORT_SUPPORTED_COLUMNS = [
        "market_cap",
        "liquidity_usd",
        "name",
        "symbol",
        "total_supply",
        "circulating_supply",
        "price_stable",
        "price_peg",

        "time",
        "created_at",
    ]
    CHAIN_SUPPORTED_VALUES = [
        56, 1, 137, 43114, 250,
        "BSC", "ETH", "POLYGON", "AVAX", "FTM",
        "bsc", "eth", "polygon", "avax", "ftm",
        "56", "1", "137", "43114", "250",
        ]
    CHAINS_NUMBER = 5
    LIMIT_LIMITS = (1, 500)
    PAGE_LIMITS = (1, 922337203685477581)
    CANDLE_LIMIT = 5000
    candle_seconds = {
        "M1": 1*60,
        "M5": 5*60,
        "M10": 10*60,
        "M15": 15*60,
        "M30": 30*60,
        "H1": 60*60,
        "H4": 4*60*60,
        "H12": 12*60*60,
        "D1": 24*60*60,
    }

    candle_limits = {
        "M1": 1*60 * 60*24 * 7, # 7 days
        "M5": 5*60 * 12*24 * 7, # 7 days
        "M10": 10*60 * 6*24 * 7, # 7 days
        "M15": 15*60 * 4*24 * 10, # 10 days
        "M30": 30*60 * 2*24 * 10, # 10 days ... > 5000 candles
        "H1": 60*60 * 24 * 14, # 14 days
        "H4": 4*60*60 * 6 * 20, # 20 days
        "H12": 12*60*60 * 2 * 20, # 20 days
        "D1": 24*60*60 * 30, # 30 days
    }

    strict_candle_limits = {
        "M1": 1*60 * 60*24 * 1, # 1 days
        "M5": 5*60 * 12*24 * 1, # 1 days
        "M10": 10*60 * 6*24 * 1, # 1 days
        "M15": 15*60 * 4*24 * 2, # 2 days
        "M30": 30*60 * 2*24 * 2, # 2 days
        "H1": 60*60 * 24 * 2, # 2 days
        "H4": 4*60*60 * 6 * 7, # 7 days
        "H12": 12*60*60 * 2 * 7, # 7 days
        "D1": 24*60*60 * 30, # 30 days
    }


    def __init__(self, auth_token: str, timeout_repetitions: int = 5, split_request: bool = True, timeout: float = 60):
        self.auth_token = auth_token
        self.timeout_repetitions = timeout_repetitions
        self.split_request = split_request
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": self.auth_token
        }
        self.api_server = self.DEFAULT_API_SERVER + self.API_VERSION
        self.assets_list = None
        self._session = requests.Session()
        retries = Retry(total=timeout_repetitions, backoff_factor=1, status_forcelist=[408, 429, 500, 503, 504])
        self._session.mount("https://", HTTPAdapter(max_retries=retries))
        self._session.headers.update(self.headers)
        self.timeout = timeout


    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        self._session.close()


    def _handle_candle_response(self, response_type: str, endpoint: str, method: str = "GET", params: Dict[str, Union[int, str]] = None, data = None, timeout: float = None):
        params["resolution"] = params["resolution"].upper()
        if "active_addresses" in endpoint or "moves" in endpoint:
            step = self.strict_candle_limits[params["resolution"]]
        else:    
            step = self.candle_limits[params["resolution"]]
        step = min(step, self.candle_seconds[params["resolution"]] * self.CANDLE_LIMIT)
        
        if not self.split_request:
            delta = params["from"] - params["to"]
            if delta/self.candle_seconds[params["resolution"]] > self.CANDLE_LIMIT or delta > step:
                raise Exception(f"Given time interval is too long for given resolution (max number of candles is {self.CANDLE_LIMIT}).")
        
        result = []
        if params["from"] is None:
            params["from"] = self.DATA_EPOCH.timestamp()
        if params["to"] is None or params["to"] > time.time():
            params["to"] = int(time.time())
        original_to = int(params["to"])
        for i in trange(int(params["from"]), int(params["to"]), step, leave=False, desc="Iterating requests to meet the limit"):
            params["from"] = i
            params["to"] = min(i + step, original_to)
            result += self._handle_response(response_type=response_type, endpoint=endpoint, method=method, params=params, data=data, timeout=timeout)
        return result


    def _handle_response(self, response_type: str, endpoint: str, method: str = "GET", params: Dict[str, Union[int, str]] = None, data = None, timeout_repetitions: int = None, timeout: float = None) -> Type[models.AnyDefinition]:
        if timeout_repetitions is None:
            timeout_repetitions = self.timeout_repetitions
        
        absolute_url = f"{self.api_server}/{endpoint}"        
        try:
            response = self._session.request(method=method, url=absolute_url, data=data, params=params, timeout=timeout if timeout else self.timeout)
            data = response.json()
            response.raise_for_status()
        except requests.exceptions.RequestException as err:
            if isinstance(data, dict) and "errors" in data and "message" in data:
                raise Exception(f"{data['message']} - {', '.join(data['errors'])}.")
            raise SystemExit(err)
        
        if data == "" or data is None:
            warnings.warn("Desired data are empty.")
            return data
        if response_type is None:
            return data

        return unmarshal.unmarshal_json(response_type, data)


    def _fill_assets(self) -> None:
        url = "assets"
        self.assets_list = self._handle_response(response_type=None, endpoint=url, method="GET")
        self.assets_list = pd.DataFrame(self.assets_list)


    def _symbol_to_contract(self, symbol: str, chain: int = None) -> str:
        """
        Translates the symbol to the contract token.

        Params
        ------
        symbol: str
            Symbol name or shortcut.
        chain : str
            Chain identifier - BSC/ETH/POLYGON; or by chain ID 56/1/137.

        Raises
        ------
        KeyError
            If symbol is not dictionary

        Returns
        -------
        contract: str
            Contract token.
        """
        if self.assets_list is None:
            self._fill_assets()

        if symbol not in self.assets_list["symbol"].values:
            raise Exception(f"Sorry, the entered symbol ({symbol}) is unknown.")
        tmp = self.assets_list.loc[symbol == self.assets_list["symbol"]]
        if tmp.shape[0] == 1:
            return tmp.iloc[0]["contract"]

        chains = tmp["chain"].unique()
        if chain is not None and chain in chains:
            tmp = self.assets_list.loc[chain == self.assets_list["chain"]]
            if tmp.shape[0] == 1:
                return tmp.iloc[0]["contract"]
            contracts = tmp["contract"].values
            raise Exception(f"""Sorry, multiple contracts belong to the symbol ({symbol}) on the specified chain ({chain}).
        You must enter a specific contract. In this case, the following are available: {contracts}""")

        raise Exception(f"""The chain has to be specified if the symbol is available on multiple of them!
        In this case, the {symbol} symbol is listed on {list(chains)} chain{"s" if len(chains)>1 else ""}.""")
    

    def _validate_contract(self, contract: str) -> None:
        if len(contract) < 3 or contract[:2] != "0x" or " " in contract:
            raise Exception("Wrong contract format.")

    
    def _validate_symbol_contract_chain(self, symbol: str, contract: str, chain: Union[str, int] = None) -> str:
        if contract is None:
            if symbol is None:
                raise ValueError("Either the symbol or the contract has to be specified.")
                # return
            if chain is not None:
                chain = self._validate_chain(chain)
            contract = self._symbol_to_contract(symbol, chain)
        else:
            self._validate_contract(contract)
        return contract


    def _validate_against(self, against: str) -> None:
        if against not in self.AGAINSTS:
            raise ValueError("Wrong value of parameter against.")


    def _validate_date(self, date) -> dt.timestamp:
        if date is None:
            return date
        if not isinstance(date, int):
            date = int(isoparse(str(date)).timestamp())
        if date < self.DATA_EPOCH.timestamp():
            warnings.warn(f"Data are available only from {self.DATA_EPOCH}.")
        return date

    
    def _validate_from__to(self, from_: Union[str, int, dt], to: Union[str, int, dt]):
        from_ = self._validate_date(from_)
        to = self._validate_date(to)
        if to:
            if to < self.DATA_EPOCH.timestamp():
                raise ValueError(F"Sorry, data are available only from {self.DATA_EPOCH}. Please select a later date.")
            if from_:
                if to <= from_:
                    raise ValueError("The to parameter must be greater than the parameter from_.")
        return from_, to


    def _validate_resolution(self, resolution: Timeframes) -> None:
        if resolution not in ["M1", "M5", "M10", "M15", "M30", "H1", "H4", "H12", "D1", "W1", "MN1"]:
            raise ValueError("The resolution must be one of the allowed values.")


    def _validate_limit(self, limit: int) -> None:
        if not limit:
            return
        if limit < self.LIMIT_LIMITS[0] or limit > self.LIMIT_LIMITS[1]:
            raise ValueError("The limit must be greater than 0 and less than or equal to 100.")

    
    def _validate_page(self, page: int) -> None:
        if not page:
            return
        if page < self.PAGE_LIMITS[0]:
            raise ValueError("The page must be greater than 0.")
        if page > self.PAGE_LIMITS[1]:
            raise ValueError("""We are sorry, but we are unable to process your page number. It is too big.
        Moreover, there aren"t that many sites.""")
    

    def _validate_sort(self, sort: str, columns: List[str]) -> None:
        if not sort:
            return
        else:
            sort = sort.lower()
        if "." in sort:
            col, order = sort.split(".")
        else:
            col = sort[1:]
            order = sort[0]
        if col in self.SORT_SUPPORTED_COLUMNS and col in columns:
            if order in ["+", "-", "asc", "desc"]:
                return
        raise ValueError("The sort parameter must match the supported values.")


    def _validate_chain(self, chain: Union[str, int]) -> int:
        if chain not in self.CHAIN_SUPPORTED_VALUES:
            raise ValueError("The chain parameter must match the supported values.")
        return self.CHAIN_SUPPORTED_VALUES[self.CHAIN_SUPPORTED_VALUES.index(chain) % self.CHAINS_NUMBER]


    def _validate_symbol_contract_against_from__to_resolution_chain(self, symbol: str, contract: str, against: str, from_, to, 
                                                              resolution: Timeframes, chain: Union[str, int]) -> Tuple[str, dt.timestamp, dt.timestamp]:
        chain = self._validate_chain(chain)
        contract = self._validate_symbol_contract_chain(symbol, contract, chain)
        self._validate_against(against)
        from_, to = self._validate_from__to(from_=from_, to=to)
        self._validate_resolution(resolution)
        return contract, from_, to

    ###################################################################################################################



    def get_farms(self, chain: Union[str, int] = "bsc", validate_params: bool = True) -> List[models.FarmResponse]:
        """
        Returns all supported farms on API.
        
        Parameters
        ----------
        chain : str
            Chain identifier - BSC/ETH/POLYGON; or by chain ID 56/1/137.
        validate_params : bool, default True
            Whether the parameters are to be validated.
        """
        
        if validate_params:
            self._validate_chain(chain)
        
        url = f"{chain}/farms"
        return self._handle_response(response_type="List[FarmResponse]", endpoint=url, method="GET")
        

    def get_optimizers_number(self, chain: Union[str, int] = "bsc", validate_params: bool = True) -> int:
        """
        Returns number of Optimizer Farms we currently support.
        
        Parameters
        ----------
        chain : str
            Chain identifier - BSC/ETH/POLYGON; or by chain ID 56/1/137.
        validate_params : bool, default True
            Whether the parameters are to be validated.
        """
        
        if validate_params:
            self._validate_chain(chain)
        
        url = f"{chain}/farms/optimizers/number"
        return self._handle_response(response_type="int", endpoint=url, method="GET")
        

    def get_yields_number(self, chain: Union[str, int] = "bsc", validate_params: bool = True) -> int:
        """
        Returns number of Yield Farms we currently support.
        
        Parameters
        ----------
        chain : str
            Chain identifier - BSC/ETH/POLYGON; or by chain ID 56/1/137.
        validate_params : bool, default True
            Whether the parameters are to be validated.
        """
        
        if validate_params:
            self._validate_chain(chain)
        
        url = f"{chain}/farms/yields/number"
        return self._handle_response(response_type="int", endpoint=url, method="GET")
        

    def get_pools(self, platform: str, chain: Union[str, int] = "bsc", validate_params: bool = True) -> models.PoolsResponse:
        """
        Returns all supported pools for given Farm(Platform).
        
        Parameters
        ----------
        chain : str
            Chain identifier - BSC/ETH/POLYGON; or by chain ID 56/1/137.
        platform : str
            Specifies platform for pools to fetch.
        validate_params : bool, default True
            Whether the parameters are to be validated.
        """
        
        if validate_params:
            self._validate_chain(chain)
        
        url = f"{chain}/farms/{platform}/pools"
        return self._handle_response(response_type="PoolsResponse", endpoint=url, method="GET")
        

    def get_pools_info(self, platform: str, chain: Union[str, int] = "bsc", validate_params: bool = True) -> models.PoolsInfoResponse:
        """
        Returns all supported pools for given Farm(Platform) and all its latest stats as APR, APY, TVL.
        
        Parameters
        ----------
        chain : str
            Chain identifier - BSC/ETH/POLYGON; or by chain ID 56/1/137.
        platform : str
            Specifies platform for pools to fetch.
        validate_params : bool, default True
            Whether the parameters are to be validated.
        """
        
        if validate_params:
            self._validate_chain(chain)
        
        url = f"{chain}/farms/{platform}/pools/info"
        return self._handle_response(response_type="PoolsInfoResponse", endpoint=url, method="GET")
        

    def get_lps(self, limit: int = None, page: int = None, sort: str = None, chain: Union[str, int] = "bsc", validate_params: bool = True) -> List[models.TokenResponseExtended]:
        """
        Returns list of LP tokens, with pagination.
        
        Parameters
        ----------
        chain : str
            Chain identifier - BSC/ETH/POLYGON; or by chain ID 56/1/137.
        limit : int
            Number of records on page.
        page : int
            Page of response data.
        sort : str
            Sorting of result, supported formats of sort and ordering:"+column"/"-column" or "column.asc"/"column.desc" ; e.g.: "+symbol" for ascending sorting by symbol.
        validate_params : bool, default True
            Whether the parameters are to be validated.
        """
        
        if validate_params:
            self._validate_chain(chain)
            self._validate_limit(limit)
            self._validate_page(page)
            self._validate_sort(sort, columns=["chain", "circulating_supply", "contract", "decimals", "liquidity_usd", "market_cap", "name", "price_change_24_h", "price_change_7_d", "price_peg", "price_usd", "symbol", "total_supply", "volume_24_h"])
        
        query_params = {
            "limit": limit,
            "page": page,
            "sort": sort,
        }
        url = f"{chain}/lps"
        return self._handle_response(response_type="List[TokenResponseExtended]", endpoint=url, method="GET", params=query_params)
        

    def get_lps_number(self, chain: Union[str, int] = "bsc", validate_params: bool = True) -> int:
        """
        Returns number of LP token saved in DB.
        
        Parameters
        ----------
        chain : str
            Chain identifier - BSC/ETH/POLYGON; or by chain ID 56/1/137.
        validate_params : bool, default True
            Whether the parameters are to be validated.
        """
        
        if validate_params:
            self._validate_chain(chain)
        
        url = f"{chain}/lps/number"
        return self._handle_response(response_type="int", endpoint=url, method="GET")
        

    def get_lp_token(self, symbol: str = None, contract: str = None, chain: Union[str, int] = "bsc", validate_params: bool = True) -> models.LPTokenResponse:
        """
        Returns basic lp token information by its contract.
        
        Parameters
        ----------
        chain : str
            Chain identifier - BSC/ETH/POLYGON; or by chain ID 56/1/137.
        contract : str
            Contract address of queried LP token.
        symbol : str, default None
            Symbol of the token.
            If it is unique on the selected chain, the contract is entered.
        validate_params : bool, default True
            Whether the parameters are to be validated.
        """
        
        if validate_params:
            contract = self._validate_symbol_contract_chain(symbol, contract, chain)
        
        url = f"{chain}/lps/{contract}"
        return self._handle_response(response_type="LPTokenResponse", endpoint=url, method="GET")
        

    def get_lps_liquidity(self, symbol: str = None, contract: str = None, from_: Union[str, int, dt] = None, to: Union[str, int, dt] = None, chain: Union[str, int] = "bsc", resolution: str = "H1", validate_params: bool = True) -> List[models.LPLiquidityResponse]:
        """
        Returns time series of liquidity for tokens of given LPToken by its contract, maximum number of candles for return is 5000.
        
        Parameters
        ----------
        chain : str
            Chain identifier - BSC/ETH/POLYGON; or by chain ID 56/1/137.
        contract : str
            Contract address of queried LP token.
        symbol : str, default None
            Symbol of the token.
            If it is unique on the selected chain, the contract is entered.
        from_ : int
            Unix timestamp of start of wanted time interval, if omitted start of unix time is used.
        to : int
            Unix timestamp of end of wanted time interval, if omitted recent time is used.
        resolution : str
            Candle resolution.
        validate_params : bool, default True
            Whether the parameters are to be validated.
        """
        
        if validate_params:
            from_, to = self._validate_from__to(from_, to)
            contract = self._validate_symbol_contract_chain(symbol, contract, chain)
            self._validate_resolution(resolution)
        
        query_params = {
            "from": from_,
            "to": to,
            "resolution": resolution,
        }
        url = f"{chain}/lps/{contract}/liquidity"
        return self._handle_candle_response(response_type="List[LPLiquidityResponse]", endpoint=url, method="GET", params=query_params)
        

    def get_lps_price(self, symbol: str = None, contract: str = None, chain: Union[str, int] = "bsc", validate_params: bool = True) -> float:
        """
        Get the most recent price of given LP token.
        
        Parameters
        ----------
        chain : str
            Chain identifier - BSC/ETH/POLYGON; or by chain ID 56/1/137.
        contract : str
            Contract address of queried LP token.
        symbol : str, default None
            Symbol of the token.
            If it is unique on the selected chain, the contract is entered.
        validate_params : bool, default True
            Whether the parameters are to be validated.
        """
        
        if validate_params:
            contract = self._validate_symbol_contract_chain(symbol, contract, chain)
        
        url = f"{chain}/lps/{contract}/price"
        return self._handle_response(response_type="float", endpoint=url, method="GET")
        

    def get_lps_swaps(self, from_wallet: str = None, token_contract: str = None, limit: int = None, page: int = None, sort: str = None, symbol: str = None, contract: str = None, from_: Union[str, int, dt] = None, to: Union[str, int, dt] = None, chain: Union[str, int] = "bsc", validate_params: bool = True) -> List[models.LPMoveResponse]:
        """
        Returns most recent swaps for given wallet and token, with pagination.
        
        Parameters
        ----------
        chain : str
            Chain identifier - BSC/ETH/POLYGON; or by chain ID 56/1/137.
        contract : str
            Contract address of queried LP token.
        symbol : str, default None
            Symbol of the token.
            If it is unique on the selected chain, the contract is entered.
        from_wallet : str
            Address of wallet.
        token_contract : str
            Contract address of queried token.
        from_ : int
            Unix timestamp of start of wanted time interval, if omitted start of unix time is used.
        to : int
            Unix timestamp of end of wanted time interval, if omitted recent time is used.
        limit : int
            Number of records on page.
        page : int
            Page of response data.
        sort : str
            Sorting of result, supported formats of sort and ordering:"+column"/"-column" or "column.asc"/"column.desc" ; e.g.: "-created_at" for starting with most recent.
        validate_params : bool, default True
            Whether the parameters are to be validated.
        """
        
        if validate_params:
            from_, to = self._validate_from__to(from_, to)
            contract = self._validate_symbol_contract_chain(symbol, contract, chain)
            self._validate_page(page)
            self._validate_sort(sort, columns=["amount_0", "amount_1", "time", "token_contract", "token_symbol"])
            self._validate_limit(limit)
        
        query_params = {
            "from_wallet": from_wallet,
            "token_contract": token_contract,
            "from": from_,
            "to": to,
            "limit": limit,
            "page": page,
            "sort": sort,
        }
        url = f"{chain}/lps/{contract}/swaps"
        return self._handle_response(response_type="List[LPMoveResponse]", endpoint=url, method="GET", params=query_params)
        

    def get_tokens(self, limit: int = None, page: int = None, sort: str = None, extended: bool = None, chain: Union[str, int] = "bsc", validate_params: bool = True) -> List[models.TokenResponseExtended]:
        """
        Returns list of top tokens by its market cap or liquidity, with pagination.
        
        Parameters
        ----------
        chain : str
            Chain identifier - BSC/ETH/POLYGON; or by chain ID 56/1/137.
        extended : bool
            Extended info about token (includes volume in last 24hours, price changes...).
        limit : int
            Number of records on page.
        page : int
            Page of response data.
        sort : str
            Sorting of result, supported formats of sort and ordering:"+column"/"-column" or "column.asc"/"column.desc" ; e.g.: "-market_cap"for descending sort by market capitalization.
        validate_params : bool, default True
            Whether the parameters are to be validated.
        """
        
        if validate_params:
            self._validate_chain(chain)
            self._validate_limit(limit)
            self._validate_page(page)
            self._validate_sort(sort, columns=["chain", "circulating_supply", "contract", "decimals", "liquidity_usd", "market_cap", "name", "price_change_24_h", "price_change_7_d", "price_peg", "price_usd", "symbol", "total_supply", "volume_24_h"])
        
        query_params = {
            "extended": extended,
            "limit": limit,
            "page": page,
            "sort": sort,
        }
        url = f"{chain}/tokens"
        return self._handle_response(response_type="List[TokenResponseExtended]", endpoint=url, method="GET", params=query_params)
        

    def get_tokens_number(self, chain: Union[str, int] = "bsc", validate_params: bool = True) -> int:
        """
        Returns number of token saved in DB.
        
        Parameters
        ----------
        chain : str
            Chain identifier - BSC/ETH/POLYGON; or by chain ID 56/1/137.
        validate_params : bool, default True
            Whether the parameters are to be validated.
        """
        
        if validate_params:
            self._validate_chain(chain)
        
        url = f"{chain}/tokens/number"
        return self._handle_response(response_type="int", endpoint=url, method="GET")
        

    def get_token(self, symbol: str = None, contract: str = None, extended: bool = None, chain: Union[str, int] = "bsc", validate_params: bool = True) -> models.TokenResponse:
        """
        Returns basic token information by its contract.
        
        Parameters
        ----------
        chain : str
            Chain identifier - BSC/ETH/POLYGON; or by chain ID 56/1/137.
        contract : str
            Contract address of queried token.
        symbol : str, default None
            Symbol of the token.
            If it is unique on the selected chain, the contract is entered.
        extended : bool
            Extended info about token: quotes etc.; default is "false".
        validate_params : bool, default True
            Whether the parameters are to be validated.
        """
        
        if validate_params:
            contract = self._validate_symbol_contract_chain(symbol, contract, chain)
        
        query_params = {
            "extended": extended,
        }
        url = f"{chain}/tokens/{contract}"
        return self._handle_response(response_type="TokenResponse", endpoint=url, method="GET", params=query_params)
        

    def get_active_addresses(self, symbol: str = None, contract: str = None, from_: Union[str, int, dt] = None, to: Union[str, int, dt] = None, chain: Union[str, int] = "bsc", resolution: str = "H1", validate_params: bool = True) -> List[models.ActiveAddressesResponse]:
        """
        Returns time series of active addresses counts for specific token for some time range.
        
        Parameters
        ----------
        chain : str
            Chain identifier - BSC/ETH/POLYGON; or by chain ID 56/1/137.
        contract : str
            Contract address of queried token.
        symbol : str, default None
            Symbol of the token.
            If it is unique on the selected chain, the contract is entered.
        from_ : int
            Unix timestamp of start of wanted time interval, if omitted start of unix time is used.
        to : int
            Unix timestamp of end of wanted time interval, if omitted recent time is used.
        resolution : str
            Candle resolution.
        validate_params : bool, default True
            Whether the parameters are to be validated.
        """
        
        if validate_params:
            from_, to = self._validate_from__to(from_, to)
            contract = self._validate_symbol_contract_chain(symbol, contract, chain)
            self._validate_resolution(resolution)
        
        query_params = {
            "from": from_,
            "to": to,
            "resolution": resolution,
        }
        url = f"{chain}/tokens/{contract}/active_addresses"
        return self._handle_candle_response(response_type="List[ActiveAddressesResponse]", endpoint=url, method="GET", params=query_params)
        

    def get_candles(self, symbol: str = None, contract: str = None, from_: Union[str, int, dt] = None, to: Union[str, int, dt] = None, chain: Union[str, int] = "bsc", resolution: str = "H1", against: str = None, platform: str = None, validate_params: bool = True) -> List[models.TokenPriceResponse]:
        """
        Returns price time series for specific token for some time range.
        
        Parameters
        ----------
        chain : str
            Chain identifier - BSC/ETH/POLYGON; or by chain ID 56/1/137.
        contract : str
            Contract address of queried token.
        symbol : str, default None
            Symbol of the token.
            If it is unique on the selected chain, the contract is entered.
        against : str
            If price should be against PEG or USD; default value is USD.
        from_ : int
            Unix timestamp of start of wanted time interval, if omitted start of unix time is used.
        to : int
            Unix timestamp of end of wanted time interval, if omitted recent time is used.
        resolution : str
            Candle resolution.
        platform : str
            Comma separated platforms from which prices are taken, as a default value is taken the biggest platform on chain.
        validate_params : bool, default True
            Whether the parameters are to be validated.
        """
        
        if validate_params:
            contract, from_, to = self._validate_symbol_contract_against_from__to_resolution_chain(symbol, contract, against, from_, to, resolution, chain)
        
        query_params = {
            "against": against,
            "from": from_,
            "to": to,
            "resolution": resolution,
            "platform": platform,
        }
        url = f"{chain}/tokens/{contract}/candles"
        return self._handle_candle_response(response_type="List[TokenPriceResponse]", endpoint=url, method="GET", params=query_params)
        

    def get_holders(self, symbol: str = None, contract: str = None, chain: Union[str, int] = "bsc", validate_params: bool = True) -> int:
        """
        Get number of all holders for given token.
        
        Parameters
        ----------
        chain : str
            Chain identifier - BSC/ETH/POLYGON; or by chain ID 56/1/137.
        contract : str
            Contract address of queried token.
        symbol : str, default None
            Symbol of the token.
            If it is unique on the selected chain, the contract is entered.
        validate_params : bool, default True
            Whether the parameters are to be validated.
        """
        
        if validate_params:
            contract = self._validate_symbol_contract_chain(symbol, contract, chain)
        
        url = f"{chain}/tokens/{contract}/holders"
        return self._handle_response(response_type="int", endpoint=url, method="GET")
        

    def get_market_cap(self, symbol: str = None, contract: str = None, chain: Union[str, int] = "bsc", validate_params: bool = True) -> float:
        """
        Calculate recent market capitalization of given token.
        
        Parameters
        ----------
        chain : str
            Chain identifier - BSC/ETH/POLYGON; or by chain ID 56/1/137.
        contract : str
            Contract address of queried token.
        symbol : str, default None
            Symbol of the token.
            If it is unique on the selected chain, the contract is entered.
        validate_params : bool, default True
            Whether the parameters are to be validated.
        """
        
        if validate_params:
            contract = self._validate_symbol_contract_chain(symbol, contract, chain)
        
        url = f"{chain}/tokens/{contract}/market_cap"
        return self._handle_response(response_type="float", endpoint=url, method="GET")
        

    def get_pairs(self, symbol: str = None, contract: str = None, chain: Union[str, int] = "bsc", validate_params: bool = True) -> Dict[str, models.LPTokenResponse]:
        """
        Returns Pancake token pairs (with Peg(e.g. BNB) and USD) for given token by its contract.
        
        Parameters
        ----------
        chain : str
            Chain identifier - BSC/ETH/POLYGON; or by chain ID 56/1/137.
        contract : str
            Contract address of queried token.
        symbol : str, default None
            Symbol of the token.
            If it is unique on the selected chain, the contract is entered.
        validate_params : bool, default True
            Whether the parameters are to be validated.
        """
        
        if validate_params:
            contract = self._validate_symbol_contract_chain(symbol, contract, chain)
        
        url = f"{chain}/tokens/{contract}/pairs"
        return self._handle_response(response_type="Dict[str, LPTokenResponse]", endpoint=url, method="GET")
        

    def get_price(self, symbol: str = None, contract: str = None, chain: Union[str, int] = "bsc", against: str = None, validate_params: bool = True) -> float:
        """
        Get the most recent price of given token.
        
        Parameters
        ----------
        chain : str
            Chain identifier - BSC/ETH/POLYGON; or by chain ID 56/1/137.
        contract : str
            Contract address of queried token.
        symbol : str, default None
            Symbol of the token.
            If it is unique on the selected chain, the contract is entered.
        against : str
            If price should be against PEG or USD; default value is USD.
        validate_params : bool, default True
            Whether the parameters are to be validated.
        """
        
        if validate_params:
            contract = self._validate_symbol_contract_chain(symbol, contract, chain)
            self._validate_against(against)
        
        query_params = {
            "against": against,
        }
        url = f"{chain}/tokens/{contract}/price"
        return self._handle_response(response_type="float", endpoint=url, method="GET", params=query_params)
        

    def get_price_change(self, symbol: str = None, contract: str = None, chain: Union[str, int] = "bsc", interval: str = "D1", against: str = None, validate_params: bool = True) -> float:
        """
        Get price change in percent of given token for given time interval.
        
        Parameters
        ----------
        chain : str
            Chain identifier - BSC/ETH/POLYGON; or by chain ID 56/1/137.
        contract : str
            Contract address of queried token.
        symbol : str, default None
            Symbol of the token.
            If it is unique on the selected chain, the contract is entered.
        against : str
            If price should be against PEG or USD; default value is USD.
        interval : str
            Historic interval for calculating change; default value is D1.
        validate_params : bool, default True
            Whether the parameters are to be validated.
        """
        
        if validate_params:
            contract = self._validate_symbol_contract_chain(symbol, contract, chain)
            self._validate_against(against)
            self._validate_resolution(interval)
        
        query_params = {
            "against": against,
            "interval": interval,
        }
        url = f"{chain}/tokens/{contract}/price/change"
        return self._handle_response(response_type="float", endpoint=url, method="GET", params=query_params)
        

    def get_swaps(self, from_wallet: str = None, lp_token: str = None, limit: int = None, page: int = None, sort: str = None, symbol: str = None, contract: str = None, from_: Union[str, int, dt] = None, to: Union[str, int, dt] = None, chain: Union[str, int] = "bsc", validate_params: bool = True) -> List[models.LPMoveResponse]:
        """
        Returns most recent swaps for given wallet and token, with pagination.
        
        Parameters
        ----------
        chain : str
            Chain identifier - BSC/ETH/POLYGON; or by chain ID 56/1/137.
        contract : str
            Contract address of queried token.
        symbol : str, default None
            Symbol of the token.
            If it is unique on the selected chain, the contract is entered.
        from_wallet : str
            Address of wallet.
        lp_token : str
            Contract address of queried LP token.
        from_ : int
            Unix timestamp of start of wanted time interval, if omitted start of unix time is used.
        to : int
            Unix timestamp of end of wanted time interval, if omitted recent time is used.
        limit : int
            Number of records on page.
        page : int
            Page of response data.
        sort : str
            Sorting of result, supported formats of sort and ordering:"+column"/"-column" or "column.asc"/"column.desc" ; e.g.: "-created_at" for starting with most recent.
        validate_params : bool, default True
            Whether the parameters are to be validated.
        """
        
        if validate_params:
            from_, to = self._validate_from__to(from_, to)
            contract = self._validate_symbol_contract_chain(symbol, contract, chain)
            self._validate_page(page)
            self._validate_sort(sort, columns=["amount_0", "amount_1", "time", "token_contract", "token_symbol"])
            self._validate_limit(limit)
        
        query_params = {
            "from_wallet": from_wallet,
            "lp_token": lp_token,
            "from": from_,
            "to": to,
            "limit": limit,
            "page": page,
            "sort": sort,
        }
        url = f"{chain}/tokens/{contract}/swaps"
        return self._handle_response(response_type="List[LPMoveResponse]", endpoint=url, method="GET", params=query_params)
        

    def get_swaps_number(self, symbol: str = None, contract: str = None, from_: Union[str, int, dt] = None, to: Union[str, int, dt] = None, chain: Union[str, int] = "bsc", resolution: str = "H1", validate_params: bool = True) -> List[models.ActiveAddressesResponse]:
        """
        Returns time series of swaps counts for specific token for some time range.
        
        Parameters
        ----------
        chain : str
            Chain identifier - BSC/ETH/POLYGON; or by chain ID 56/1/137.
        contract : str
            Contract address of queried token.
        symbol : str, default None
            Symbol of the token.
            If it is unique on the selected chain, the contract is entered.
        from_ : int
            Unix timestamp of start of wanted time interval, if omitted start of unix time is used.
        to : int
            Unix timestamp of end of wanted time interval, if omitted recent time is used.
        resolution : str
            Candle resolution.
        validate_params : bool, default True
            Whether the parameters are to be validated.
        """
        
        if validate_params:
            from_, to = self._validate_from__to(from_, to)
            contract = self._validate_symbol_contract_chain(symbol, contract, chain)
            self._validate_resolution(resolution)
        
        query_params = {
            "from": from_,
            "to": to,
            "resolution": resolution,
        }
        url = f"{chain}/tokens/{contract}/swaps/number"
        return self._handle_candle_response(response_type="List[ActiveAddressesResponse]", endpoint=url, method="GET", params=query_params)
        

    def get_volumes(self, symbol: str = None, contract: str = None, from_: Union[str, int, dt] = None, to: Union[str, int, dt] = None, chain: Union[str, int] = "bsc", resolution: str = "H1", validate_params: bool = True) -> List[models.TradedVolumeResponse]:
        """
        Returns calculated total traded volume for specific token in given time range.
        
        Parameters
        ----------
        chain : str
            Chain identifier - BSC/ETH/POLYGON; or by chain ID 56/1/137.
        contract : str
            Contract address of queried token.
        symbol : str, default None
            Symbol of the token.
            If it is unique on the selected chain, the contract is entered.
        from_ : int
            Unix timestamp of start of wanted time interval, if omitted start of unix time is used.
        to : int
            Unix timestamp of end of wanted time interval, if omitted recent time is used.
        resolution : str
            Candle resolution.
        validate_params : bool, default True
            Whether the parameters are to be validated.
        """
        
        if validate_params:
            from_, to = self._validate_from__to(from_, to)
            contract = self._validate_symbol_contract_chain(symbol, contract, chain)
            self._validate_resolution(resolution)
        
        query_params = {
            "from": from_,
            "to": to,
            "resolution": resolution,
        }
        url = f"{chain}/tokens/{contract}/volumes"
        return self._handle_candle_response(response_type="List[TradedVolumeResponse]", endpoint=url, method="GET", params=query_params)
        

    def get_volumes_change(self, symbol: str = None, contract: str = None, chain: Union[str, int] = "bsc", interval: str = "D1", validate_params: bool = True) -> float:
        """
        Get change in traded volume in 24h of given token for given time interval.
        
        Parameters
        ----------
        chain : str
            Chain identifier - BSC/ETH/POLYGON; or by chain ID 56/1/137.
        contract : str
            Contract address of queried token.
        symbol : str, default None
            Symbol of the token.
            If it is unique on the selected chain, the contract is entered.
        interval : str
            Historic interval for calculating change, default value is D1.
        validate_params : bool, default True
            Whether the parameters are to be validated.
        """
        
        if validate_params:
            contract = self._validate_symbol_contract_chain(symbol, contract, chain)
            self._validate_resolution(interval)
        
        query_params = {
            "interval": interval,
        }
        url = f"{chain}/tokens/{contract}/volumes/change"
        return self._handle_response(response_type="float", endpoint=url, method="GET", params=query_params)
        

    def get_volumes_latest(self, symbol: str = None, contract: str = None, chain: Union[str, int] = "bsc", interval: str = "D1", validate_params: bool = True) -> float:
        """
        Get volume of all trades in given interval for given token.
        
        Parameters
        ----------
        chain : str
            Chain identifier - BSC/ETH/POLYGON; or by chain ID 56/1/137.
        contract : str
            Contract address of queried token.
        symbol : str, default None
            Symbol of the token.
            If it is unique on the selected chain, the contract is entered.
        interval : str
            Interval for calculating volume; default value is D1.
        validate_params : bool, default True
            Whether the parameters are to be validated.
        """
        
        if validate_params:
            contract = self._validate_symbol_contract_chain(symbol, contract, chain)
            self._validate_resolution(interval)
        
        query_params = {
            "interval": interval,
        }
        url = f"{chain}/tokens/{contract}/volumes/latest"
        return self._handle_response(response_type="float", endpoint=url, method="GET", params=query_params)
        

    def get_wallets_number(self, chain: Union[str, int] = "bsc", validate_params: bool = True) -> int:
        """
        Returns number of unique addresses saved in DB.
        
        Parameters
        ----------
        chain : str
            Chain identifier - BSC/ETH/POLYGON; or by chain ID 56/1/137.
        validate_params : bool, default True
            Whether the parameters are to be validated.
        """
        
        if validate_params:
            self._validate_chain(chain)
        
        url = f"{chain}/wallets/number"
        return self._handle_response(response_type="int", endpoint=url, method="GET")
        

    def get_wallets_farm_portfolio(self, address: str, chain: Union[str, int] = "bsc", validate_params: bool = True) -> Dict[str, List[models.FarmsPortfolioResponse]]:
        """
        Returns balances from all supported farms for given address.
        
        Parameters
        ----------
        chain : str
            Chain identifier - BSC/ETH/POLYGON; or by chain ID 56/1/137.
        address : str
            Address of wallet to be queried.
        validate_params : bool, default True
            Whether the parameters are to be validated.
        """
        
        if validate_params:
            self._validate_chain(chain)
        
        url = f"{chain}/wallets/{address}/farm_portfolio"
        return self._handle_response(response_type="FarmsPortfolioResponse", endpoint=url, method="GET")
        

    def get_wallets_historic_farm_portfolio(self, address: str, from_: Union[str, int, dt] = None, to: Union[str, int, dt] = None, chain: Union[str, int] = "bsc", validate_params: bool = True) -> List[models.PortfolioResponse]:
        """
        Returns historic balances on all supported farms for given wallet address, wallet should be whitelisted.
        
        Parameters
        ----------
        chain : str
            Chain identifier - BSC/ETH/POLYGON; or by chain ID 56/1/137.
        address : str
            Address of whitelisted wallet.
        from_ : int
            Unix timestamp of start of wanted time interval, if omitted start of unix time is used.
        to : int
            Unix timestamp of end of wanted time interval, if omitted recent time is used.
        validate_params : bool, default True
            Whether the parameters are to be validated.
        """
        
        if validate_params:
            from_, to = self._validate_from__to(from_, to)
            self._validate_chain(chain)
        
        query_params = {
            "from": from_,
            "to": to,
        }
        url = f"{chain}/wallets/{address}/historic_farm_portfolio"
        return self._handle_response(response_type="List[PortfolioResponse]", endpoint=url, method="GET", params=query_params)
        

    def get_wallets_historic_portfolio(self, address: str, from_: Union[str, int, dt] = None, to: Union[str, int, dt] = None, chain: Union[str, int] = "bsc", validate_params: bool = True) -> List[models.PortfolioResponse]:
        """
        Returns historic balances of all tokens held by given address, provided address should be whitelisted.
        
        Parameters
        ----------
        chain : str
            Chain identifier - BSC/ETH/POLYGON; or by chain ID 56/1/137.
        address : str
            Address of whitelisted wallet.
        from_ : int
            Unix timestamp of start of wanted time interval, if omitted start of unix time is used.
        to : int
            Unix timestamp of end of wanted time interval, if omitted recent time is used.
        validate_params : bool, default True
            Whether the parameters are to be validated.
        """
        
        if validate_params:
            from_, to = self._validate_from__to(from_, to)
            self._validate_chain(chain)
        
        query_params = {
            "from": from_,
            "to": to,
        }
        url = f"{chain}/wallets/{address}/historic_portfolio"
        return self._handle_response(response_type="List[PortfolioResponse]", endpoint=url, method="GET", params=query_params)
        

    def get_wallets_moves(self, address: str, token_contract: str = None, from_: Union[str, int, dt] = None, to: Union[str, int, dt] = None, chain: Union[str, int] = "bsc", resolution: str = "H1", validate_params: bool = True) -> List[models.WalletMoveResponse]:
        """
        Returns all moves as a time series for given wallet and specified tokens for some time range.
        
        Parameters
        ----------
        chain : str
            Chain identifier - BSC/ETH/POLYGON; or by chain ID 56/1/137.
        address : str
            Wallet address of required moves.
        token_contract : str
            Comma separated contracts of tokens for which moves should be fetched.
        from_ : int
            Unix timestamp of start of wanted time interval, if omitted start of unix time is used.
        to : int
            Unix timestamp of end of wanted time interval, if omitted recent time is used.
        resolution : str
            Candle resolution.
        validate_params : bool, default True
            Whether the parameters are to be validated.
        """
        
        if validate_params:
            from_, to = self._validate_from__to(from_, to)
            self._validate_chain(chain)
            self._validate_resolution(resolution)
        
        query_params = {
            "token_contract": token_contract,
            "from": from_,
            "to": to,
            "resolution": resolution,
        }
        url = f"{chain}/wallets/{address}/moves"
        return self._handle_candle_response(response_type="List[WalletMoveResponse]", endpoint=url, method="GET", params=query_params)
        

    def get_wallets_portfolio(self, address: str, chain: Union[str, int] = "bsc", validate_params: bool = True) -> List[models.TokenPortfolioResponse]:
        """
        Returns balances of all tokens held by given address.
        
        Parameters
        ----------
        chain : str
            Chain identifier - BSC/ETH/POLYGON; or by chain ID 56/1/137.
        address : str
            Address of wallet to be queried.
        validate_params : bool, default True
            Whether the parameters are to be validated.
        """
        
        if validate_params:
            self._validate_chain(chain)
        
        url = f"{chain}/wallets/{address}/portfolio"
        return self._handle_response(response_type="List[TokenPortfolioResponse]", endpoint=url, method="GET")
        

    def get_wallets_swaps(self, address: str, token_contract: str = None, lp_token: str = None, limit: int = None, page: int = None, sort: str = None, from_: Union[str, int, dt] = None, to: Union[str, int, dt] = None, chain: Union[str, int] = "bsc", validate_params: bool = True) -> List[models.LPMoveResponse]:
        """
        Returns most recent swaps for given wallet and token, with pagination.
        
        Parameters
        ----------
        chain : str
            Chain identifier - BSC/ETH/POLYGON; or by chain ID 56/1/137.
        address : str
            Address of wallet.
        token_contract : str
            Contract address of queried token.
        lp_token : str
            Contract address of queried LP token.
        from_ : int
            Unix timestamp of start of wanted time interval, if omitted start of unix time is used.
        to : int
            Unix timestamp of end of wanted time interval, if omitted recent time is used.
        limit : int
            Number of records on page.
        page : int
            Page of response data.
        sort : str
            Sorting of result, supported formats of sort and ordering:"+column"/"-column" or "column.asc"/"column.desc" ; e.g.: "-created_at" for starting with most recent.
        validate_params : bool, default True
            Whether the parameters are to be validated.
        """
        
        if validate_params:
            from_, to = self._validate_from__to(from_, to)
            self._validate_sort(sort, columns=["amount_0", "amount_1", "time", "token_contract", "token_symbol"])
            self._validate_page(page)
            self._validate_chain(chain)
            self._validate_limit(limit)
        
        query_params = {
            "token_contract": token_contract,
            "lp_token": lp_token,
            "from": from_,
            "to": to,
            "limit": limit,
            "page": page,
            "sort": sort,
        }
        url = f"{chain}/wallets/{address}/swaps"
        return self._handle_response(response_type="List[LPMoveResponse]", endpoint=url, method="GET", params=query_params)
        

    def get_wallets_txs(self, address: str, limit: int = None, page: int = None, from_: Union[str, int, dt] = None, to: Union[str, int, dt] = None, chain: Union[str, int] = "bsc", validate_params: bool = True) -> List[models.TransactionResponse]:
        """
        Returns all transactions for given wallet, with pagination.
        
        Parameters
        ----------
        chain : str
            Chain identifier - BSC/ETH/POLYGON; or by chain ID 56/1/137.
        address : str
            Address of wallet.
        from_ : int
            Unix timestamp of start of wanted time interval, if omitted start of unix time is used.
        to : int
            Unix timestamp of end of wanted time interval, if omitted recent time is used.
        limit : int
            Number of records on page.
        page : int
            Page of response data.
        validate_params : bool, default True
            Whether the parameters are to be validated.
        """
        
        if validate_params:
            from_, to = self._validate_from__to(from_, to)
            self._validate_page(page)
            self._validate_chain(chain)
            self._validate_limit(limit)
        
        query_params = {
            "from": from_,
            "to": to,
            "limit": limit,
            "page": page,
        }
        url = f"{chain}/wallets/{address}/txs"
        return self._handle_response(response_type="List[TransactionResponse]", endpoint=url, method="GET", params=query_params)
        

    def get_assets(self, chain: str = None, symbol: str = None, contract: str = None, validate_params: bool = True) -> List[models.AvailableAsset]:
        """
        Returns list of assets that are used for tagging publications data filtered by query params.
        
        Parameters
        ----------
        chain : str
            Chain id identifier 56/1/137 etc.
        validate_params : bool, default True
            Whether the parameters are to be validated.
        """
        
        if validate_params:
            chain = self._validate_chain(chain)

        
        query_params = {
            "chain": chain,
        }
        url = "assets"
        return self._handle_response(response_type="List[AvailableAsset]", endpoint=url, method="GET", params=query_params)
        

    def get_discord(self, from_: Union[str, int, dt], limit: int, tag: str = None, validate_params: bool = True) -> List[models.DiscordPublicMessage]:
        """
        Returns list of discord messages according to filtration specified in the request.
        
        Parameters
        ----------
        from_ : int
            Specified timestamp used in GTE condition.
        limit : int
            Max number of returned items.
        tag : str
            Optional tag.
        validate_params : bool, default True
            Whether the parameters are to be validated.
        """
        
        if validate_params:
            from_ = self._validate_date(from_)
            self._validate_limit(limit)
        
        query_params = {
            "from": from_,
            "limit": limit,
            "tag": tag,
        }
        url = "discord"
        return self._handle_response(response_type="List[DiscordPublicMessage]", endpoint=url, method="GET", params=query_params)
        

    def get_publications(self, from_: Union[str, int, dt], limit: int, tag: str = None, validate_params: bool = True) -> List[models.PublicReadable]:
        """
        Returns list of publications according to filtration specified in the request.
        
        Parameters
        ----------
        from_ : int
            Specified timestamp used in GTE condition.
        limit : int
            Max number of returned items.
        tag : str
            Optional tag.
        validate_params : bool, default True
            Whether the parameters are to be validated.
        """
        
        if validate_params:
            from_ = self._validate_date(from_)
            self._validate_limit(limit)
        
        query_params = {
            "from": from_,
            "limit": limit,
            "tag": tag,
        }
        url = "publications"
        return self._handle_response(response_type="List[PublicReadable]", endpoint=url, method="GET", params=query_params)
        

    def get_reddit(self, from_: Union[str, int, dt], limit: int, tag: str = None, validate_params: bool = True) -> List[models.Readable]:
        """
        Returns list of reddit posts according to filtration specified in the request.
        
        Parameters
        ----------
        from_ : int
            Specified timestamp used in GTE condition.
        limit : int
            Max number of returned items.
        tag : str
            Optional tag.
        validate_params : bool, default True
            Whether the parameters are to be validated.
        """
        
        if validate_params:
            from_ = self._validate_date(from_)
            self._validate_limit(limit)
        
        query_params = {
            "from": from_,
            "limit": limit,
            "tag": tag,
        }
        url = "reddit"
        return self._handle_response(response_type="List[Readable]", endpoint=url, method="GET", params=query_params)
        

    def get_telegram(self, from_: Union[str, int, dt], limit: int, tag: str = None, validate_params: bool = True) -> List[models.TelegramPublicMessage]:
        """
        Returns list of telegram messages according to filtration specified in the request.
        
        Parameters
        ----------
        from_ : int
            Specified timestamp used in GTE condition.
        limit : int
            Max number of returned items.
        tag : str
            Optional tag.
        validate_params : bool, default True
            Whether the parameters are to be validated.
        """
        
        if validate_params:
            from_ = self._validate_date(from_)
            self._validate_limit(limit)
        
        query_params = {
            "from": from_,
            "limit": limit,
            "tag": tag,
        }
        url = "telegram"
        return self._handle_response(response_type="List[TelegramPublicMessage]", endpoint=url, method="GET", params=query_params)
        

    def get_twitter(self, from_: Union[str, int, dt], limit: int, tag: str = None, validate_params: bool = True) -> List[models.TweetPublic]:
        """
        Returns list of tweets according to filtration specified in the request.
        
        Parameters
        ----------
        from_ : int
            Specified timestamp used in GTE condition.
        limit : int
            Max number of returned items.
        tag : str
            Optional tag.
        validate_params : bool, default True
            Whether the parameters are to be validated.
        """
        
        if validate_params:
            from_ = self._validate_date(from_)
            self._validate_limit(limit)
        
        query_params = {
            "from": from_,
            "limit": limit,
            "tag": tag,
        }
        url = "twitter"
        return self._handle_response(response_type="List[TweetPublic]", endpoint=url, method="GET", params=query_params)
        

    ###################################################################################################################
    ############################################     DERIVED FUNCTIONS     ############################################
    ###################################################################################################################

    def get_OHLCV(self, symbol: str = None, contract: str = None, from_: Union[str, int, dt] = None, to: Union[str, int, dt] = None, chain: Union[str, int] = "bsc", resolution: str = "H1", against: str = "USD", platform: str = None, validate_params: bool = True) -> pd.DataFrame:
        """
        Get price data (in OHLC format) with volume.

        Parameters
        ----------
        chain : str
            Chain identifier - BSC/ETH/POLYGON; or by chain ID 56/1/137.
        symbol : str, default None
            Symbol of the token.
            If it is unique on the selected chain, the contract is entered.
        contract : str
            Contract address of queried token.
        against : str
            If price should be against PEG or USD.
        from_ : int
            Unix timestamp of start of wanted time interval, if omitted start of unix time is used.
        to : int
            Unix timestamp of end of wanted time interval, if omitted recent time is used.
        resolution : str
            Candle resolution.
        platform : str
            Comma separated platforms from which prices are taken, as a default value is taken the biggest platform on chain.
        validate_params : bool, default True
            Whether the parameters are to be validated.

        Returns
        -------
        data: pd.DataFrame
            Price data with volume.
        """
        if validate_params:
            contract, from_, to = self._validate_symbol_contract_against_from__to_resolution_chain(symbol, contract, against, from_, to, resolution, chain)

        prices = self.get_candles(symbol=symbol, contract=contract, from_=from_, to=to, chain=chain, resolution=resolution, against=against, platform=platform, validate_params=False)
        # if prices are empty, stop execution
        if prices == []:
            raise ValueError("Price data are empty. It does not make sence to continue.")
        
        prices = pd.DataFrame(
            [p.to_dict() for p in prices],
        ).set_index("time")
        
        volumes = self.get_volumes(symbol=symbol, contract=contract, from_=from_, to=to, chain=chain, resolution=resolution, validate_params=False)
        # if volumes are empty, stop execution
        if volumes == []:
            raise ValueError("Volume data are empty. It does not make sence to continue.")
        volumes = pd.DataFrame(
            [p.__dict__ for p in volumes],
        ).set_index("time")
        return prices.join(volumes)


    def get_OHLCVAS(self, contract: str = None, symbol: str = None, from_: Union[str, int, dt] = None, to: Union[str, int, dt] = None, chain: Union[str, int] = "bsc", resolution: str = "H1", against: str = "USD", platform: str = None, validate_params: bool = True) -> pd.DataFrame:
        """
        Get price data (in OHLC format) with volume, active addresses number and swap number.

        This method returns all available data in form of time-series (with desired resolution).

        Parameters
        ----------
        chain : str
            Chain identifier - BSC/ETH/POLYGON; or by chain ID 56/1/137.
        symbol : str, default None
            Symbol of the token.
            If it is unique on the selected chain, the contract is entered.
        contract : str
            Contract address of queried token.
        against : str
            If price should be against PEG or USD.
        from_ : int
            Unix timestamp of start of wanted time interval, if omitted start of unix time is used.
        to : int
            Unix timestamp of end of wanted time interval, if omitted recent time is used.
        resolution : str
            Candle resolution.
        platform : str
            Comma separated platforms from which prices are taken, as a default value is taken the biggest platform on chain.
        validate_params : bool, default True
            Whether the parameters are to be validated.

        Returns
        -------
        data: pd.DataFrame
            Price data with volume.
        """
        if validate_params:
            contract, from_, to = self._validate_symbol_contract_against_from__to_resolution_chain(symbol, contract, against, from_, to, resolution, chain)

        result = self.get_OHLCV(symbol=symbol, contract=contract, from_=from_, to=to, chain=chain, resolution=resolution, against=against, platform=platform, validate_params=False)
        # if prices are empty, stop execution
        if result.empty:
            raise ValueError("OHLCV data are empty. It does not make sence to continue.")
        
        addresses = self.get_active_addresses(symbol=symbol, contract=contract, from_=from_, to=to, chain=chain, resolution=resolution, validate_params=False)
        # if addresses are empty, stop execution
        if addresses == []:
            raise ValueError("Addresses data are empty. It does not make sence to continue.")
        addresses = pd.DataFrame(
            [p.__dict__ for p in addresses],
        ).set_index("time").rename(columns={"count": "addresses_count"})
        result = result.join(addresses)

        swaps = self.get_swaps_number(symbol=symbol, contract=contract, from_=from_, to=to, chain=chain, resolution=resolution, validate_params=False)
        # if swaps are empty, stop execution
        if swaps == []:
            raise ValueError("Swaps data are empty. It does not make sence to continue.")
        swaps = pd.DataFrame(
            [p.__dict__ for p in swaps],
        ).set_index("time").rename(columns={"count": "swaps_count"})
        result = result.join(swaps).fillna(0)

        return result


    ############################################     PLOTTING METHODS     ############################################
    
    def _plot_1d_data(self, data: pd.DataFrame, title: str, kind: str = "line", backend: str = "matplotlib", **kwargs):
        """
        Helper method for plotting 1-dimensional data.

        Parameters
        ----------
        kind : str
            The kind of plot to produce:
                - "line" : line plot (default)
                - "bar" : vertical bar plot
                - "barh" : horizontal bar plot
                - "hist" : histogram
                - "box" : boxplot
                - "kde" : Kernel Density Estimation plot
                - "density" : same as "kde"
                - "area" : area plot
                - "pie" : pie plot
                - "scatter" : scatter plot (DataFrame only)
                - "hexbin" : hexbin plot (DataFrame only)
        backend : str, default None
            Backend to use instead of the backend specified in the option
            ``plotting.backend``. For instance, "matplotlib". Alternatively, to
            specify the ``plotting.backend`` for the whole session, set
            ``pd.options.plotting.backend``.
            .. versionadded:: 1.0.0
        **kwargs
            Options to pass to matplotlib plotting method.
        
        Returns
        -------
        :class:`matplotlib.axes.Axes` or numpy.ndarray of them
            If the backend is not the default matplotlib one, the return value
            will be the object returned by the backend.
        """
        return data.plot(
            title = title,
            kind = kind,
            backend = backend,
            **kwargs
        )


    def plot_volumes(self, symbol: str = None, contract: str = None, from_: Union[str, int, dt] = None, to: Union[str, int, dt] = None, chain: Union[str, int] = "bsc", resolution: str = "H1", validate_params: bool = True,
                    kind: str = "line", backend: str = "matplotlib", **kwargs):
        """
        Method for plotting the volume of the selected symbol for the required interval.

        Parameters
        ----------
        chain : str
            Chain identifier - BSC/ETH/POLYGON; or by chain ID 56/1/137.
        symbol : str, default None
            Symbol of the token.
            If it is unique on the selected chain, the contract is entered.
        contract : str
            Contract address of queried token.
        from_ : int
            Unix timestamp of start of wanted time interval, if omitted start of unix time is used.
        to : int
            Unix timestamp of end of wanted time interval, if omitted recent time is used.
        resolution : str
            Candle resolution.
        validate_params : bool, default True
            Whether the parameters are to be validated.
        kind : str
            The kind of plot to produce:
                - "line" : line plot (default)
                - "bar" : vertical bar plot
                - "barh" : horizontal bar plot
                - "hist" : histogram
                - "box" : boxplot
                - "kde" : Kernel Density Estimation plot
                - "density" : same as "kde"
                - "area" : area plot
                - "pie" : pie plot
                - "scatter" : scatter plot (DataFrame only)
                - "hexbin" : hexbin plot (DataFrame only)
        backend : str, default None
            Backend to use instead of the backend specified in the option
            ``plotting.backend``. For instance, "matplotlib". Alternatively, to
            specify the ``plotting.backend`` for the whole session, set
            ``pd.options.plotting.backend``.
            .. versionadded:: 1.0.0
        **kwargs
            Options to pass to matplotlib plotting method.

        Returns
        -------
        :class:`matplotlib.axes.Axes` or numpy.ndarray of them
            If the backend is not the default matplotlib one, the return value
            will be the object returned by the backend.
        """
        volumes = self.get_volumes(symbol=symbol, contract=contract, from_=from_, to=to, chain=chain, resolution=resolution, validate_params=validate_params)
        # if volumes are empty, stop execution
        if volumes == []:
            raise ValueError("Volume data are empty. It does not make sence to continue.")
        volumes = pd.DataFrame(
            [p.to_dict() for p in volumes],
        ).set_index("time")

        return self._plot_1d_data(
            data=volumes,
            title=f"Volume of {symbol.upper() if symbol else contract} Token",
            kind=kind,
            backend=backend,
            **kwargs
        )


    def plot_swaps_number(self, symbol: str = None, contract: str = None, from_: Union[str, int, dt] = None, to: Union[str, int, dt] = None, chain: Union[str, int] = "bsc", resolution: str = "H1", validate_params: bool = True,
                    kind: str = "line", backend: str = "matplotlib", **kwargs):
        """
        Method for plotting the swaps number of the selected symbol for the required interval.

        Parameters
        ----------
        chain : str
            Chain identifier - BSC/ETH/POLYGON; or by chain ID 56/1/137.
        symbol : str, default None
            Symbol of the token.
            If it is unique on the selected chain, the contract is entered.
        contract : str
            Contract address of queried token.
        from_ : int
            Unix timestamp of start of wanted time interval, if omitted start of unix time is used.
        to : int
            Unix timestamp of end of wanted time interval, if omitted recent time is used.
        resolution : str
            Candle resolution.
        validate_params : bool, default True
            Whether the parameters are to be validated.
        kind : str
            The kind of plot to produce:
                - "line" : line plot (default)
                - "bar" : vertical bar plot
                - "barh" : horizontal bar plot
                - "hist" : histogram
                - "box" : boxplot
                - "kde" : Kernel Density Estimation plot
                - "density" : same as "kde"
                - "area" : area plot
                - "pie" : pie plot
                - "scatter" : scatter plot (DataFrame only)
                - "hexbin" : hexbin plot (DataFrame only)
        backend : str, default None
            Backend to use instead of the backend specified in the option
            ``plotting.backend``. For instance, "matplotlib". Alternatively, to
            specify the ``plotting.backend`` for the whole session, set
            ``pd.options.plotting.backend``.
            .. versionadded:: 1.0.0
        **kwargs
            Options to pass to matplotlib plotting method.

        Returns
        -------
        :class:`matplotlib.axes.Axes` or numpy.ndarray of them
            If the backend is not the default matplotlib one, the return value
            will be the object returned by the backend.
        """
        swaps = self.get_swaps_number(symbol=symbol, contract=contract, from_=from_, to=to, chain=chain, resolution=resolution, validate_params=validate_params)
        # if swaps are empty, stop execution
        if swaps == []:
            raise ValueError("Swaps data are empty. It does not make sence to continue.")
        swaps = pd.DataFrame(
            [p.to_dict() for p in swaps],
        ).set_index("time")

        return self._plot_1d_data(
            data=swaps,
            title=f"Swaps Number of {symbol.upper() if symbol else contract} Token",
            kind=kind,
            backend=backend,
            **kwargs
        )
    

    def plot_active_addresses(self, contract: str = None, symbol: str = None, from_: Union[str, int, dt] = None, to: Union[str, int, dt] = None, chain: Union[str, int] = "bsc", resolution: str = "H1", validate_params: bool = True,
                        kind: str = "line", backend: str = "matplotlib", **kwargs):
        """
        Method for plotting the active addresses number of the selected symbol for the required interval.

        Parameters
        ----------
        chain : str
            Chain identifier - BSC/ETH/POLYGON; or by chain ID 56/1/137.
        symbol : str, default None
            Symbol of the token.
            If it is unique on the selected chain, the contract is entered.
        contract : str
            Contract address of queried token.
        against : str
            If price should be against PEG or USD.
        from_ : int
            Unix timestamp of start of wanted time interval, if omitted start of unix time is used.
        to : int
            Unix timestamp of end of wanted time interval, if omitted recent time is used.
        resolution : str
            Candle resolution.
        validate_params : bool, default True
            Whether the parameters are to be validated.
        kind : str
            The kind of plot to produce:
                - "line" : line plot (default)
                - "bar" : vertical bar plot
                - "barh" : horizontal bar plot
                - "hist" : histogram
                - "box" : boxplot
                - "kde" : Kernel Density Estimation plot
                - "density" : same as "kde"
                - "area" : area plot
                - "pie" : pie plot
                - "scatter" : scatter plot (DataFrame only)
                - "hexbin" : hexbin plot (DataFrame only)
        backend : str, default None
            Backend to use instead of the backend specified in the option
            ``plotting.backend``. For instance, "matplotlib". Alternatively, to
            specify the ``plotting.backend`` for the whole session, set
            ``pd.options.plotting.backend``.
            .. versionadded:: 1.0.0
        **kwargs
            Options to pass to matplotlib plotting method.

        Returns
        -------
        :class:`matplotlib.axes.Axes` or numpy.ndarray of them
            If the backend is not the default matplotlib one, the return value
            will be the object returned by the backend.
        """
        addresses = self.get_active_addresses(contract=contract, symbol=symbol, from_=from_, to=to, chain=chain, resolution=resolution, validate_params=validate_params)
        # if addresses are empty, stop execution
        if addresses == []:
            raise ValueError("Addresses data are empty. It does not make sence to continue.")
        addresses = pd.DataFrame(
            [p.to_dict() for p in addresses],
        ).set_index("time")

        return self._plot_1d_data(
            data=addresses,
            title=f"Number of active addresses of {symbol.upper() if symbol else contract} Token",
            kind=kind,
            backend=backend,
            **kwargs
        )


    def plot_wallets_moves(self, address: str, token_contract: str = None, from_: Union[str, int, dt] = None, to: Union[str, int, dt] = None, chain: Union[str, int] = "bsc", resolution: str = "H1", validate_params: bool = True,
                            kind: str = "bar", backend: str = "matplotlib", **kwargs):
        """
        Method for plotting the moves of the selected wallet for the required interval.

        Parameters
        ----------
        chain : str
            Chain identifier - BSC/ETH/POLYGON; or by chain ID 56/1/137.
        address : str
            Wallet address of required moves.
        token_contract : str
            Comma separated contracts of tokens for which moves should be fetched.
        from_ : int
            Unix timestamp of start of wanted time interval, if omitted start of unix time is used.
        to : int
            Unix timestamp of end of wanted time interval, if omitted recent time is used.
        resolution : str
            Candle resolution.
        validate_params : bool, default True
            Whether the parameters are to be validated.
        kind : str
            The kind of plot to produce:
                - "line" : line plot (default)
                - "bar" : vertical bar plot
                - "barh" : horizontal bar plot
                - "hist" : histogram
                - "box" : boxplot
                - "kde" : Kernel Density Estimation plot
                - "density" : same as "kde"
                - "area" : area plot
                - "pie" : pie plot
                - "scatter" : scatter plot (DataFrame only)
                - "hexbin" : hexbin plot (DataFrame only)
        backend : str, default None
            Backend to use instead of the backend specified in the option
            ``plotting.backend``. For instance, "matplotlib". Alternatively, to
            specify the ``plotting.backend`` for the whole session, set
            ``pd.options.plotting.backend``.
            .. versionadded:: 1.0.0
        **kwargs
            Options to pass to matplotlib plotting method.

        Returns
        -------
        :class:`matplotlib.axes.Axes` or numpy.ndarray of them
            If the backend is not the default matplotlib one, the return value
            will be the object returned by the backend.
        """
        moves = self.get_wallets_moves(
            address = address,
            chain=chain,
            token_contract=token_contract,
            from_=from_,
            to=to,
            resolution=resolution,
            validate_params=validate_params,
            )
        # if moves are empty, stop execution
        if moves == []:
            raise ValueError("Data of moves are empty. It does not make sence to continue.")
        moves = pd.DataFrame(
            [p.to_dict() for p in moves],
        ).set_index("time")
        
        return self._plot_1d_data(
            data=moves["amount"],
            title=f"Moves of {address}",
            kind=kind,
            backend=backend,
            **kwargs
        )


    def plot_candles(self, platform: str = None, contract: str = None, symbol: str = None, from_: Union[str, int, dt] = None, to: Union[str, int, dt] = None, chain: Union[str, int] = "bsc", resolution: str = "H1", against: str = "USD", validate_params: bool = True,
                    kind: str = "line", backend: str = None, **kwargs):
        """
        Method for plotting the prices of the selected symbol for the required interval.

        Parameters
        ----------
        chain : str
            Chain identifier - BSC/ETH/POLYGON; or by chain ID 56/1/137.
        symbol : str, default None
            Symbol of the token.
            If it is unique on the selected chain, the contract is entered.
        contract : str
            Contract address of queried token.
        against : str
            If price should be against PEG or USD.
        from_ : int
            Unix timestamp of start of wanted time interval, if omitted start of unix time is used.
        to : int
            Unix timestamp of end of wanted time interval, if omitted recent time is used.
        resolution : str
            Candle resolution.
        platform : str
            Comma separated platforms from which prices are taken, as a default value is taken the biggest platform on chain.
        validate_params : bool, default True
            Whether the parameters are to be validated.
        kind : str
            The kind of plot to produce:
                - "line" : line plot (default)
                - "bar" : vertical bar plot
                - "barh" : horizontal bar plot
                - "hist" : histogram
                - "box" : boxplot
                - "kde" : Kernel Density Estimation plot
                - "density" : same as "kde"
                - "area" : area plot
                - "pie" : pie plot
                - "scatter" : scatter plot (DataFrame only)
                - "hexbin" : hexbin plot (DataFrame only)
            Used only if the backend differs from the available one.
        backend : str, default None
            Backend to use for plotting.
            Only "matplotlib" and "plotly" are available for this method.
        **kwargs
            Options to pass to matplotlib plotting method.

        Returns
        -------
        :class:`matplotlib.axes.Axes` or numpy.ndarray of them
            If the backend is not the default matplotlib one, the return value
            will be the object returned by the backend.
        """
        pricess = self.get_candles(symbol=symbol, contract=contract, from_=from_, to=to, chain=chain, resolution=resolution, against=against, platform=platform, validate_params=validate_params)
        # if pricess are empty, stop execution
        if pricess == []:
            raise ValueError("Prices data are empty. It does not make sence to continue.")
        df = pd.DataFrame(
            [p.to_dict() for p in pricess],
        ).set_index("time")

        if backend == "matplotlib" or backend is None:
            width = 1
            width2 = 0.1
            dfup = df[df["close"] >= df["open"]]
            dfdown = df[df["close"] < df["open"]]

            plt.figure(**kwargs)
            plt.bar(dfup.index, dfup["close"] - dfup["open"], width, bottom = dfup["open"], color = "g")
            plt.bar(dfup.index, dfup["high"] - dfup["close"], width2, bottom = dfup["close"], color = "g")
            plt.bar(dfup.index, dfup["low"] - dfup["open"], width2, bottom = dfup["open"], color = "g")

            plt.bar(dfdown.index, dfdown["close"] - dfdown["open"], width, bottom = dfdown["open"], color = "r")
            plt.bar(dfdown.index, dfdown["high"] - dfdown["open"], width2, bottom = dfdown["open"], color = "r")
            plt.bar(dfdown.index, dfdown["low"] - dfdown["close"], width2,  bottom = dfdown["close"], color = "r")
            plt.xticks(rotation = 90)
            plt.xlabel("date")
            plt.ylabel("price")
            plt.title(f"Prices of {symbol.upper() if symbol else contract} Token")
            plt.grid()
            return
        
        if backend == "plotly":
            fig = make_subplots(
                rows=1, cols=1, shared_xaxes=True, 
                vertical_spacing=0.07,
                subplot_titles=(f"Prices of {symbol.upper() if symbol else contract} Token",),
                row_width=[1],
                **kwargs,
                )

            fig.add_trace(go.Candlestick(x=df.index,
                                        open=df["open"], high=df["high"],
                                        low=df["low"], close=df["close"],
                                        name="price"
                                        ),
                        )
            fig.layout.yaxis.fixedrange = False
            fig.layout.yaxis.autorange = True
            fig.layout.xaxis.fixedrange = False
            fig.layout.xaxis.autorange = True
            return fig

        warnings.warn("Other backends are not (yet) supporter in this method. It might not work.")
        return df.plot(
            title = f"Prices of {symbol.upper() if symbol else contract} Token",
            kind=kind,
            backend=backend,
            **kwargs,
        )
