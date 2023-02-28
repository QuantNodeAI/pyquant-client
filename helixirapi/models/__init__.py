import typing

from .definitions import ActiveAddressesResponse
from .definitions import AvailableAsset
from .definitions import Balance
from .definitions import BalanceMove
from .definitions import BalanceMoveLP
from .definitions import BasicOptimizerPool
from .definitions import BasicOptimizerPoolInfo
from .definitions import BasicPool
from .definitions import BasicPoolInfo
from .definitions import Definition
from .definitions import DiscordPublicMessage
from .definitions import Domain
from .definitions import FarmPortfolio
from .definitions import FarmResponse
from .definitions import FarmsPortfolioResponse
from .definitions import LPLiquidityResponse
from .definitions import LPMoveResponse
from .definitions import LPTokenResponse
from .definitions import Liquidity
from .definitions import MarketDepth
from .definitions import PoolBalance
from .definitions import PoolsInfoResponse
from .definitions import PoolsResponse
from .definitions import PortfolioResponse
from .definitions import PriceTick
from .definitions import PublicReadable
from .definitions import Readable
from .definitions import Tag
from .definitions import TelegramPublicMessage
from .definitions import TokenPortfolioResponse
from .definitions import TokenPriceResponse
from .definitions import TokenResponse
from .definitions import TokenResponseExtended
from .definitions import TradedVolumeResponse
from .definitions import TransactionResponse
from .definitions import TweetPublic
from .definitions import VolumeTick
from .definitions import WalletMoveResponse
from .definitions import WhitelistedAddress

AnyDefinition = typing.TypeVar("AnyDefinition", bound=Definition)

name_to_class: typing.Dict[str, typing.Callable[[], typing.Type[AnyDefinition]]] = {
    "TokenPortfolioResponse": TokenPortfolioResponse,
    "BalanceMove": BalanceMove,
    "LPMoveResponse": LPMoveResponse,
    "TokenResponse": TokenResponse,
    "Domain": Domain,
    "TradedVolumeResponse": TradedVolumeResponse,
    "WhitelistedAddress": WhitelistedAddress,
    "TweetPublic": TweetPublic,
    "PublicReadable": PublicReadable,
    "Liquidity": Liquidity,
    "Tag": Tag,
    "LPLiquidityResponse": LPLiquidityResponse,
    "PoolsResponse": PoolsResponse,
    "PoolBalance": PoolBalance,
    "DiscordPublicMessage": DiscordPublicMessage,
    "PortfolioResponse": PortfolioResponse,
    "TelegramPublicMessage": TelegramPublicMessage,
    "PoolsInfoResponse": PoolsInfoResponse,
    "BasicPoolInfo": BasicPoolInfo,
    "FarmPortfolio": FarmPortfolio,
    "LPTokenResponse": LPTokenResponse,
    "AvailableAsset": AvailableAsset,
    "VolumeTick": VolumeTick,
    "Readable": Readable,
    "BalanceMoveLP": BalanceMoveLP,
    "TransactionResponse": TransactionResponse,
    "FarmResponse": FarmResponse,
    "TokenResponseExtended": TokenResponseExtended,
    "TokenPriceResponse": TokenPriceResponse,
    "BasicOptimizerPool": BasicOptimizerPool,
    "PriceTick": PriceTick,
    "BasicOptimizerPoolInfo": BasicOptimizerPoolInfo,
    "FarmsPortfolioResponse": FarmsPortfolioResponse,
    "WalletMoveResponse": WalletMoveResponse,
    "ActiveAddressesResponse": ActiveAddressesResponse,
    "Balance": Balance,
    "BasicPool": BasicPool,
    "MarketDepth": MarketDepth
}
