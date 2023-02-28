import keyword
from typing import List, Dict, Any

from dateutil.parser import isoparse

from helixirapi import models


class Definition:
    _api_name_to_python: Dict[str, str]
    _attribute_is_primitive: Dict[str, bool]
    _attributes_to_types: Dict[str, Any]

    def __repr__(self) -> str:
        attributes = ""
        for key, value in vars(self).items():
            value = str(value).replace("\n", "\n\t")
            attributes += f"\t{key} = {value},\n"
        return f"{self.__class__.__name__}(\n{attributes})"

    def to_dict(self):
        return self.__dict__

    def unmarshal_json(self, input_json):
        if isinstance(input_json, list):
            list_attribute_name = list(self._api_name_to_python.values())[0]
            if list_attribute_name in self._attributes_to_types:
                list_type = self._attributes_to_types[list_attribute_name]
                known_type = list_type.split("[")[1][:-1]
                list_items = self._unmarshal_json_list(input_json, known_type)
            else:
                list_items = input_json
            self.__setattr__(list_attribute_name, list_items)
            return self
        if isinstance(input_json, dict):
            self._unmarshal_json_object(input_json)
            return self
        if isinstance(input_json, float) or isinstance(input_json, int):
            return input_json

    @staticmethod
    def _unmarshal_json_list(input_json, known_type):
        items = []
        for item in input_json:
            new_item = models.name_to_class[known_type]()
            items.append(new_item._unmarshal_json_object(item))

        return items

    def _unmarshal_json_object(self, input_json):
        for key, value in input_json.items():
            if key in self._api_name_to_python:
                attribute_name = self._api_name_to_python[key]
                if not self._attribute_is_primitive[attribute_name]:
                    if attribute_name in self._attributes_to_types:
                        model = self._attributes_to_types[attribute_name]
                        if "List" in str(model):
                            response_type = f"List[{model.__args__[0].__name__}]"
                            value = models.unmarshal.unmarshal_json(response_type, input_json[key])
                        else:
                            value = model().unmarshal_json(input_json[key])
                else:
                    value = self._attributes_to_types[attribute_name](value)
            else:
                attribute_name = key + ('_' if keyword.iskeyword(key) else '')

            self.__setattr__(attribute_name, value)
        return self


class PoolBalance(Definition):
    _api_name_to_python = {
        "balance": "balance",
        "pending_reward": "pending_reward",
        "pending_reward_price": "pending_reward_price",
        "price": "price",
        "reward_token": "reward_token",
        "token": "token",
        "token_address": "token_address",
    }

    _attribute_is_primitive = {
        "balance": True,
        "pending_reward": True,
        "pending_reward_price": True,
        "price": True,
        "reward_token": True,
        "token": True,
        "token_address": True,
    }

    _attributes_to_types = {
        "balance": float,
        "pending_reward": float,
        "pending_reward_price": float,
        "price": float,
        "reward_token": str,
        "token": str,
        "token_address": str,
    }

    def __init__(self):
        self.balance: float
        self.pending_reward: float
        self.pending_reward_price: float
        self.price: float
        self.reward_token: str
        self.token: str
        self.token_address: str


class WhitelistedAddress(Definition):
    _api_name_to_python = {
        "address": "address",
        "id": "id",
    }

    _attribute_is_primitive = {
        "address": True,
        "id": True,
    }

    _attributes_to_types = {
        "address": str,
        "id": int,
    }

    def __init__(self):
        self.address: str
        self.id: int


class FarmPortfolio(Definition):
    _api_name_to_python = {
        "farm_icon": "farm_icon",
        "farm_name": "farm_name",
        "farm_true_name": "farm_true_name",
        "pools_balance": "pools_balance",
    }

    _attribute_is_primitive = {
        "farm_icon": True,
        "farm_name": True,
        "farm_true_name": True,
        "pools_balance": False,
    }

    _attributes_to_types = {
        "farm_icon": str,
        "farm_name": str,
        "farm_true_name": str,
        "pools_balance": List[PoolBalance],
    }

    def __init__(self):
        self.farm_icon: str
        self.farm_name: str
        self.farm_true_name: str
        self.pools_balance: List[PoolBalance]


class TokenResponse(Definition):
    _api_name_to_python = {
        "active": "active",
        "chain": "chain",
        "circulating_supply": "circulating_supply",
        "contract": "contract",
        "decimals": "decimals",
        "id": "id",
        "name": "name",
        "symbol": "symbol",
        "total_supply": "total_supply",
    }

    _attribute_is_primitive = {
        "active": True,
        "chain": True,
        "circulating_supply": True,
        "contract": True,
        "decimals": True,
        "id": True,
        "name": True,
        "symbol": True,
        "total_supply": True,
    }

    _attributes_to_types = {
        "active": bool,
        "chain": str,
        "circulating_supply": float,
        "contract": str,
        "decimals": float,
        "id": int,
        "name": str,
        "symbol": str,
        "total_supply": float,
    }

    def __init__(self):
        self.active: bool
        self.chain: str
        self.circulating_supply: float
        self.contract: str
        self.decimals: float
        self.id: int
        self.name: str
        self.symbol: str
        self.total_supply: float


class BasicPoolInfo(Definition):
    _api_name_to_python = {
        "apr": "apr",
        "apy": "apy",
        "reward_token": "reward_token",
        "token": "token",
        "token_address": "token_address",
        "tvl": "tvl",
    }

    _attribute_is_primitive = {
        "apr": True,
        "apy": True,
        "reward_token": True,
        "token": True,
        "token_address": True,
        "tvl": True,
    }

    _attributes_to_types = {
        "apr": float,
        "apy": float,
        "reward_token": str,
        "token": str,
        "token_address": str,
        "tvl": float,
    }

    def __init__(self):
        self.apr: float
        self.apy: float
        self.reward_token: str
        self.token: str
        self.token_address: str
        self.tvl: float


class BasicOptimizerPoolInfo(Definition):
    _api_name_to_python = {
        "apy": "apy",
        "farm_apr": "farm_apr",
        "from_platform": "from_platform",
        "reward_token": "reward_token",
        "rewards_apr": "rewards_apr",
        "token": "token",
        "token_address": "token_address",
        "tvl": "tvl",
    }

    _attribute_is_primitive = {
        "apy": True,
        "farm_apr": True,
        "from_platform": True,
        "reward_token": True,
        "rewards_apr": True,
        "token": True,
        "token_address": True,
        "tvl": True,
    }

    _attributes_to_types = {
        "apy": float,
        "farm_apr": float,
        "from_platform": str,
        "reward_token": str,
        "rewards_apr": float,
        "token": str,
        "token_address": str,
        "tvl": float,
    }

    def __init__(self):
        self.apy: float
        self.farm_apr: float
        self.from_platform: str
        self.reward_token: str
        self.rewards_apr: float
        self.token: str
        self.token_address: str
        self.tvl: float


class BasicPoolInfo(Definition):
    _api_name_to_python = {
        "apr": "apr",
        "apy": "apy",
        "reward_token": "reward_token",
        "token": "token",
        "token_address": "token_address",
        "tvl": "tvl",
    }

    _attribute_is_primitive = {
        "apr": True,
        "apy": True,
        "reward_token": True,
        "token": True,
        "token_address": True,
        "tvl": True,
    }

    _attributes_to_types = {
        "apr": float,
        "apy": float,
        "reward_token": str,
        "token": str,
        "token_address": str,
        "tvl": float,
    }

    def __init__(self):
        self.apr: float
        self.apy: float
        self.reward_token: str
        self.token: str
        self.token_address: str
        self.tvl: float


class BasicOptimizerPoolInfo(Definition):
    _api_name_to_python = {
        "apy": "apy",
        "farm_apr": "farm_apr",
        "from_platform": "from_platform",
        "reward_token": "reward_token",
        "rewards_apr": "rewards_apr",
        "token": "token",
        "token_address": "token_address",
        "tvl": "tvl",
    }

    _attribute_is_primitive = {
        "apy": True,
        "farm_apr": True,
        "from_platform": True,
        "reward_token": True,
        "rewards_apr": True,
        "token": True,
        "token_address": True,
        "tvl": True,
    }

    _attributes_to_types = {
        "apy": float,
        "farm_apr": float,
        "from_platform": str,
        "reward_token": str,
        "rewards_apr": float,
        "token": str,
        "token_address": str,
        "tvl": float,
    }

    def __init__(self):
        self.apy: float
        self.farm_apr: float
        self.from_platform: str
        self.reward_token: str
        self.rewards_apr: float
        self.token: str
        self.token_address: str
        self.tvl: float


class Domain(Definition):
    _api_name_to_python = {
        "authority": "authority",
        "url": "url",
    }

    _attribute_is_primitive = {
        "authority": True,
        "url": True,
    }

    _attributes_to_types = {
        "authority": int,
        "url": str,
    }

    def __init__(self):
        self.authority: int
        self.url: str


class Tag(Definition):
    _api_name_to_python = {
        "id": "id",
        "tag": "tag",
    }

    _attribute_is_primitive = {
        "id": True,
        "tag": True,
    }

    _attributes_to_types = {
        "id": int,
        "tag": str,
    }

    def __init__(self):
        self.id: int
        self.tag: str


class BasicPool(Definition):
    _api_name_to_python = {
        "reward_token": "reward_token",
        "token": "token",
        "token_address": "token_address",
    }

    _attribute_is_primitive = {
        "reward_token": True,
        "token": True,
        "token_address": True,
    }

    _attributes_to_types = {
        "reward_token": str,
        "token": str,
        "token_address": str,
    }

    def __init__(self):
        self.reward_token: str
        self.token: str
        self.token_address: str


class BasicOptimizerPool(Definition):
    _api_name_to_python = {
        "from_platform": "from_platform",
        "reward_token": "reward_token",
        "token": "token",
        "token_address": "token_address",
    }

    _attribute_is_primitive = {
        "from_platform": True,
        "reward_token": True,
        "token": True,
        "token_address": True,
    }

    _attributes_to_types = {
        "from_platform": str,
        "reward_token": str,
        "token": str,
        "token_address": str,
    }

    def __init__(self):
        self.from_platform: str
        self.reward_token: str
        self.token: str
        self.token_address: str


class Balance(Definition):
    _api_name_to_python = {
        "createdAt": "createdAt",
        "portfolio": "portfolio",
        "wallet": "wallet",
        "walletID": "walletID",
    }

    _attribute_is_primitive = {
        "createdAt": True,
        "portfolio": True,
        "wallet": False,
        "walletID": True,
    }

    _attributes_to_types = {
        "createdAt": str,
        "portfolio": str,
        "wallet": WhitelistedAddress,
        "walletID": int,
    }

    def __init__(self):
        self.createdAt: str
        self.portfolio: str
        self.wallet: WhitelistedAddress
        self.walletID: int


class BalanceMove(Definition):
    _api_name_to_python = {
        "move": "move",
        "timestamp": "timestamp",
        "token_id": "token_id",
        "wallet_id": "wallet_id",
    }

    _attribute_is_primitive = {
        "move": True,
        "timestamp": True,
        "token_id": True,
        "wallet_id": True,
    }

    _attributes_to_types = {
        "move": float,
        "timestamp": str,
        "token_id": int,
        "wallet_id": int,
    }

    def __init__(self):
        self.move: float
        self.timestamp: str
        self.token_id: int
        self.wallet_id: int


class BalanceMoveLP(Definition):
    _api_name_to_python = {
        "move": "move",
        "timestamp": "timestamp",
        "token_id": "token_id",
        "wallet_id": "wallet_id",
    }

    _attribute_is_primitive = {
        "move": True,
        "timestamp": True,
        "token_id": True,
        "wallet_id": True,
    }

    _attributes_to_types = {
        "move": float,
        "timestamp": str,
        "token_id": int,
        "wallet_id": int,
    }

    def __init__(self):
        self.move: float
        self.timestamp: str
        self.token_id: int
        self.wallet_id: int


class Liquidity(Definition):
    _api_name_to_python = {
        "platform_id": "platform_id",
        "reserve_0": "reserve_0",
        "reserve_1": "reserve_1",
        "timestamp": "timestamp",
        "token_id": "token_id",
    }

    _attribute_is_primitive = {
        "platform_id": True,
        "reserve_0": True,
        "reserve_1": True,
        "timestamp": True,
        "token_id": True,
    }

    _attributes_to_types = {
        "platform_id": int,
        "reserve_0": float,
        "reserve_1": float,
        "timestamp": str,
        "token_id": int,
    }

    def __init__(self):
        self.platform_id: int
        self.reserve_0: float
        self.reserve_1: float
        self.timestamp: str
        self.token_id: int


class PriceTick(Definition):
    _api_name_to_python = {
        "circulating_supply": "circulating_supply",
        "platform_id": "platform_id",
        "price_peg": "price_peg",
        "price_stable": "price_stable",
        "timestamp": "timestamp",
        "token_id": "token_id",
    }

    _attribute_is_primitive = {
        "circulating_supply": True,
        "platform_id": True,
        "price_peg": True,
        "price_stable": True,
        "timestamp": True,
        "token_id": True,
    }

    _attributes_to_types = {
        "circulating_supply": float,
        "platform_id": int,
        "price_peg": float,
        "price_stable": float,
        "timestamp": str,
        "token_id": int,
    }

    def __init__(self):
        self.circulating_supply: float
        self.platform_id: int
        self.price_peg: float
        self.price_stable: float
        self.timestamp: str
        self.token_id: int


class VolumeTick(Definition):
    _api_name_to_python = {
        "platform_id": "platform_id",
        "timestamp": "timestamp",
        "token_id": "token_id",
        "volume": "volume",
    }

    _attribute_is_primitive = {
        "platform_id": True,
        "timestamp": True,
        "token_id": True,
        "volume": True,
    }

    _attributes_to_types = {
        "platform_id": int,
        "timestamp": str,
        "token_id": int,
        "volume": float,
    }

    def __init__(self):
        self.platform_id: int
        self.timestamp: str
        self.token_id: int
        self.volume: float


class ActiveAddressesResponse(Definition):
    _api_name_to_python = {
        "count": "count",
        "time": "time",
    }

    _attribute_is_primitive = {
        "count": True,
        "time": True,
    }

    _attributes_to_types = {
        "count": int,
        "time": isoparse,
    }

    def __init__(self):
        self.count: int
        self.time: isoparse


class FarmResponse(Definition):
    _api_name_to_python = {
        "name": "name",
        "true_name": "true_name",
        "tvl": "tvl",
    }

    _attribute_is_primitive = {
        "name": True,
        "true_name": True,
        "tvl": True,
    }

    _attributes_to_types = {
        "name": str,
        "true_name": str,
        "tvl": float,
    }

    def __init__(self):
        self.name: str
        self.true_name: str
        self.tvl: float


class FarmsPortfolioResponse(Definition):
    _api_name_to_python = {
        "lp_pools": "lp_pools",
        "optimizer_lp_pools": "optimizer_lp_pools",
        "optimizer_single_asset_pools": "optimizer_single_asset_pools",
        "single_asset_pools": "single_asset_pools",
    }

    _attribute_is_primitive = {
        "lp_pools": False,
        "optimizer_lp_pools": False,
        "optimizer_single_asset_pools": False,
        "single_asset_pools": False,
    }

    _attributes_to_types = {
        "lp_pools": List[FarmPortfolio],
        "optimizer_lp_pools": List[FarmPortfolio],
        "optimizer_single_asset_pools": List[FarmPortfolio],
        "single_asset_pools": List[FarmPortfolio],
    }

    def __init__(self):
        self.lp_pools: List[FarmPortfolio]
        self.optimizer_lp_pools: List[FarmPortfolio]
        self.optimizer_single_asset_pools: List[FarmPortfolio]
        self.single_asset_pools: List[FarmPortfolio]


class LPLiquidityResponse(Definition):
    _api_name_to_python = {
        "liquidity_0": "liquidity_0",
        "liquidity_1": "liquidity_1",
        "time": "time",
    }

    _attribute_is_primitive = {
        "liquidity_0": True,
        "liquidity_1": True,
        "time": True,
    }

    _attributes_to_types = {
        "liquidity_0": float,
        "liquidity_1": float,
        "time": isoparse,
    }

    def __init__(self):
        self.liquidity_0: float
        self.liquidity_1: float
        self.time: isoparse


class LPMoveResponse(Definition):
    _api_name_to_python = {
        "amount_0": "amount_0",
        "amount_1": "amount_1",
        "time": "time",
        "token_contract": "token_contract",
        "token_symbol": "token_symbol",
    }

    _attribute_is_primitive = {
        "amount_0": True,
        "amount_1": True,
        "time": True,
        "token_contract": True,
        "token_symbol": True,
    }

    _attributes_to_types = {
        "amount_0": float,
        "amount_1": float,
        "time": isoparse,
        "token_contract": str,
        "token_symbol": str,
    }

    def __init__(self):
        self.amount_0: float
        self.amount_1: float
        self.time: isoparse
        self.token_contract: str
        self.token_symbol: str


class LPTokenResponse(Definition):
    _api_name_to_python = {
        "chain": "chain",
        "contract": "contract",
        "decimals": "decimals",
        "id": "id",
        "name": "name",
        "symbol": "symbol",
        "token_0": "token_0",
        "token_1": "token_1",
        "total_supply": "total_supply",
    }

    _attribute_is_primitive = {
        "chain": True,
        "contract": True,
        "decimals": True,
        "id": True,
        "name": True,
        "symbol": True,
        "token_0": False,
        "token_1": False,
        "total_supply": True,
    }

    _attributes_to_types = {
        "chain": str,
        "contract": str,
        "decimals": float,
        "id": int,
        "name": str,
        "symbol": str,
        "token_0": TokenResponse,
        "token_1": TokenResponse,
        "total_supply": float,
    }

    def __init__(self):
        self.chain: str
        self.contract: str
        self.decimals: float
        self.id: int
        self.name: str
        self.symbol: str
        self.token_0: TokenResponse
        self.token_1: TokenResponse
        self.total_supply: float


class PoolsInfoResponse(Definition):
    _api_name_to_python = {
        "lp_pools": "lp_pools",
        "optimizer_lp_pools": "optimizer_lp_pools",
        "optimizer_single_asset_pools": "optimizer_single_asset_pools",
        "single_asset_pools": "single_asset_pools",
    }

    _attribute_is_primitive = {
        "lp_pools": False,
        "optimizer_lp_pools": False,
        "optimizer_single_asset_pools": False,
        "single_asset_pools": False,
    }

    _attributes_to_types = {
        "lp_pools": List[BasicPoolInfo],
        "optimizer_lp_pools": List[BasicOptimizerPoolInfo],
        "optimizer_single_asset_pools": List[BasicOptimizerPoolInfo],
        "single_asset_pools": List[BasicPoolInfo],
    }

    def __init__(self):
        self.lp_pools: List[BasicPoolInfo]
        self.optimizer_lp_pools: List[BasicOptimizerPoolInfo]
        self.optimizer_single_asset_pools: List[BasicOptimizerPoolInfo]
        self.single_asset_pools: List[BasicPoolInfo]


class PoolsResponse(Definition):
    _api_name_to_python = {
        "lp_pools": "lp_pools",
        "optimizer_lp_pools": "optimizer_lp_pools",
        "optimizer_single_asset_pools": "optimizer_single_asset_pools",
        "single_asset_pools": "single_asset_pools",
    }

    _attribute_is_primitive = {
        "lp_pools": False,
        "optimizer_lp_pools": False,
        "optimizer_single_asset_pools": False,
        "single_asset_pools": False,
    }

    _attributes_to_types = {
        "lp_pools": List[BasicPool],
        "optimizer_lp_pools": List[BasicOptimizerPool],
        "optimizer_single_asset_pools": List[BasicOptimizerPool],
        "single_asset_pools": List[BasicPool],
    }

    def __init__(self):
        self.lp_pools: List[BasicPool]
        self.optimizer_lp_pools: List[BasicOptimizerPool]
        self.optimizer_single_asset_pools: List[BasicOptimizerPool]
        self.single_asset_pools: List[BasicPool]


class PortfolioResponse(Definition):
    _api_name_to_python = {
        "portfolio": "portfolio",
        "time": "time",
    }

    _attribute_is_primitive = {
        "portfolio": True,
        "time": True,
    }

    _attributes_to_types = {
        "portfolio": str,
        "time": isoparse,
    }

    def __init__(self):
        self.portfolio: str
        self.time: isoparse


class TokenPortfolioResponse(Definition):
    _api_name_to_python = {
        "balance": "balance",
        "token_address": "token_address",
        "token_icon": "token_icon",
        "token_name": "token_name",
        "token_symbol": "token_symbol",
        "usd_value": "usd_value",
    }

    _attribute_is_primitive = {
        "balance": True,
        "token_address": True,
        "token_icon": True,
        "token_name": True,
        "token_symbol": True,
        "usd_value": True,
    }

    _attributes_to_types = {
        "balance": float,
        "token_address": str,
        "token_icon": str,
        "token_name": str,
        "token_symbol": str,
        "usd_value": float,
    }

    def __init__(self):
        self.balance: float
        self.token_address: str
        self.token_icon: str
        self.token_name: str
        self.token_symbol: str
        self.usd_value: float


class TokenPriceResponse(Definition):
    _api_name_to_python = {
        "close": "close",
        "high": "high",
        "low": "low",
        "open": "open",
        "time": "time",
    }

    _attribute_is_primitive = {
        "close": True,
        "high": True,
        "low": True,
        "open": True,
        "time": True,
    }

    _attributes_to_types = {
        "close": float,
        "high": float,
        "low": float,
        "open": float,
        "time": isoparse,
    }

    def __init__(self):
        self.close: float
        self.high: float
        self.low: float
        self.open: float
        self.time: isoparse


class TokenResponseExtended(Definition):
    _api_name_to_python = {
        "active": "active",
        "chain": "chain",
        "circulating_supply": "circulating_supply",
        "contract": "contract",
        "decimals": "decimals",
        "id": "id",
        "liquidity_usd": "liquidity_usd",
        "market_cap": "market_cap",
        "name": "name",
        "price_change_24_h": "price_change_24_h",
        "price_change_7_d": "price_change_7_d",
        "price_peg": "price_peg",
        "price_usd": "price_usd",
        "symbol": "symbol",
        "total_supply": "total_supply",
        "volume_24_h": "volume_24_h",
    }

    _attribute_is_primitive = {
        "active": True,
        "chain": True,
        "circulating_supply": True,
        "contract": True,
        "decimals": True,
        "id": True,
        "liquidity_usd": True,
        "market_cap": True,
        "name": True,
        "price_change_24_h": True,
        "price_change_7_d": True,
        "price_peg": True,
        "price_usd": True,
        "symbol": True,
        "total_supply": True,
        "volume_24_h": True,
    }

    _attributes_to_types = {
        "active": bool,
        "chain": str,
        "circulating_supply": float,
        "contract": str,
        "decimals": float,
        "id": int,
        "liquidity_usd": float,
        "market_cap": float,
        "name": str,
        "price_change_24_h": float,
        "price_change_7_d": float,
        "price_peg": float,
        "price_usd": float,
        "symbol": str,
        "total_supply": float,
        "volume_24_h": float,
    }

    def __init__(self):
        self.active: bool
        self.chain: str
        self.circulating_supply: float
        self.contract: str
        self.decimals: float
        self.id: int
        self.liquidity_usd: float
        self.market_cap: float
        self.name: str
        self.price_change_24_h: float
        self.price_change_7_d: float
        self.price_peg: float
        self.price_usd: float
        self.symbol: str
        self.total_supply: float
        self.volume_24_h: float


class TradedVolumeResponse(Definition):
    _api_name_to_python = {
        "time": "time",
        "volume": "volume",
    }

    _attribute_is_primitive = {
        "time": True,
        "volume": True,
    }

    _attributes_to_types = {
        "time": isoparse,
        "volume": float,
    }

    def __init__(self):
        self.time: isoparse
        self.volume: float


class TransactionResponse(Definition):
    _api_name_to_python = {
        "block": "block",
        "from_address": "from_address",
        "time": "time",
        "to_address": "to_address",
        "tx_fee": "tx_fee",
        "tx_hash": "tx_hash",
        "value": "value",
    }

    _attribute_is_primitive = {
        "block": True,
        "from_address": True,
        "time": True,
        "to_address": True,
        "tx_fee": True,
        "tx_hash": True,
        "value": True,
    }

    _attributes_to_types = {
        "block": int,
        "from_address": str,
        "time": isoparse,
        "to_address": str,
        "tx_fee": float,
        "tx_hash": str,
        "value": float,
    }

    def __init__(self):
        self.block: int
        self.from_address: str
        self.time: isoparse
        self.to_address: str
        self.tx_fee: float
        self.tx_hash: str
        self.value: float


class WalletMoveResponse(Definition):
    _api_name_to_python = {
        "amount": "amount",
        "time": "time",
        "token": "token",
    }

    _attribute_is_primitive = {
        "amount": True,
        "time": True,
        "token": True,
    }

    _attributes_to_types = {
        "amount": float,
        "time": isoparse,
        "token": str,
    }

    def __init__(self):
        self.amount: float
        self.time: isoparse
        self.token: str


class MarketDepth(Definition):
    _api_name_to_python = {
        "time": "time",
        "current_price": "current_price",
        "depth": "depth",
    }

    _attribute_is_primitive = {
        "time": True,
        "current_price": True,
        "depth": True,
    }

    _attributes_to_types = {
        "time": isoparse,
        "current_price": float,
        "depth": str,
    }

    def __init__(self):
        self.time: isoparse
        self.current_price: float
        self.depth: str


class AvailableAsset(Definition):
    _api_name_to_python = {
        "chain": "chain",
        "contract": "contract",
        "is_default": "is_default",
        "symbol": "symbol",
    }

    _attribute_is_primitive = {
        "chain": True,
        "contract": True,
        "is_default": True,
        "symbol": True,
    }

    _attributes_to_types = {
        "chain": int,
        "contract": str,
        "is_default": bool,
        "symbol": str,
    }

    def __init__(self):
        self.chain: int
        self.contract: str
        self.is_default: bool
        self.symbol: str


class DiscordPublicMessage(Definition):
    _api_name_to_python = {
        "content": "content",
        "created_at": "created_at",
        "id": "id",
    }

    _attribute_is_primitive = {
        "content": True,
        "created_at": True,
        "id": True,
    }

    _attributes_to_types = {
        "content": str,
        "created_at": isoparse,
        "id": int,
    }

    def __init__(self):
        self.content: str
        self.created_at: isoparse
        self.id: int


class PublicReadable(Definition):
    _api_name_to_python = {
        "created_at": "created_at",
        "domain": "domain",
        "source": "source",
        "text": "text",
        "title": "title",
    }

    _attribute_is_primitive = {
        "created_at": True,
        "domain": False,
        "source": True,
        "text": True,
        "title": True,
    }

    _attributes_to_types = {
        "created_at": isoparse,
        "domain": Domain,
        "source": str,
        "text": str,
        "title": str,
    }

    def __init__(self):
        self.created_at: isoparse
        self.domain: Domain
        self.source: str
        self.text: str
        self.title: str


class Readable(Definition):
    _api_name_to_python = {
        "comment_count": "comment_count",
        "created_at": "created_at",
        "domain": "domain",
        "emotion": "emotion",
        "id": "id",
        "published_at": "published_at",
        "source": "source",
        "tags": "tags",
        "title": "title",
        "view_count": "view_count",
    }

    _attribute_is_primitive = {
        "comment_count": True,
        "created_at": True,
        "domain": False,
        "emotion": True,
        "id": True,
        "published_at": True,
        "source": True,
        "tags": False,
        "title": True,
        "view_count": True,
    }

    _attributes_to_types = {
        "comment_count": int,
        "created_at": isoparse,
        "domain": Domain,
        "emotion": float,
        "id": int,
        "published_at": str,
        "source": str,
        "tags": List[Tag],
        "title": str,
        "view_count": int,
    }

    def __init__(self):
        self.comment_count: int
        self.created_at: isoparse
        self.domain: Domain
        self.emotion: float
        self.id: int
        self.published_at: str
        self.source: str
        self.tags: List[Tag]
        self.title: str
        self.view_count: int


class TelegramPublicMessage(Definition):
    _api_name_to_python = {
        "content": "content",
        "created_at": "created_at",
        "message_id": "message_id",
        "sent_at": "sent_at",
    }

    _attribute_is_primitive = {
        "content": True,
        "created_at": True,
        "message_id": True,
        "sent_at": True,
    }

    _attributes_to_types = {
        "content": str,
        "created_at": isoparse,
        "message_id": int,
        "sent_at": isoparse,
    }

    def __init__(self):
        self.content: str
        self.created_at: isoparse
        self.message_id: int
        self.sent_at: isoparse


class TweetPublic(Definition):
    _api_name_to_python = {
        "content": "content",
        "created_at": "created_at",
        "tweet_id": "tweet_id",
    }

    _attribute_is_primitive = {
        "content": True,
        "created_at": True,
        "tweet_id": True,
    }

    _attributes_to_types = {
        "content": str,
        "created_at": isoparse,
        "tweet_id": int,
    }

    def __init__(self):
        self.content: str
        self.created_at: isoparse
        self.tweet_id: int
