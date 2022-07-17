# Helixir API client

[![Python](https://img.shields.io/badge/Python-14354C?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache_2.0-yellow.svg)](LICENSE)
[![Medium](https://img.shields.io/badge/Medium-12100E?style=flat&logo=medium&logoColor=white)](https://medium.com/)
[![Telegram](https://img.shields.io/badge/Telegram-2CA5E0?style=flat&logo=telegram&logoColor=white)]()
[![GitHub](https://img.shields.io/badge/GitHub-100000?style=flat&logo=github&logoColor=white)](https://github.com/HelixirLabs)
[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://github.com/HelixirLabs/helixir-api-client/examples/Example.ipynb)

_Python client library for the [Helixir API](https://helixir.io/helixir-api)_


## Table of Content
<details>
<summary>Click to expand!</summary>

- [Description](#description)
- [Installation](#installation)
- [Features](#features)
- [Usage](#usage)
- [License](#license)
</details>


## Description
_Helixir_ provides simple to use **API for on-chain data** for numerous blockchains, news & social media data, and comprehensive quant models.
All under one roof.

_Helixir_ is a data provider that offers on-chain data from EVM compatible blockchains, news & social media data and models.
With our analytical tools, you can find **best entry points** for your trades, **analyze price data** or **create machine learning models** for cryptocurrencies with ease.

Check out the [website](https://helixir.io/) for more information!


## Installation

The library can be installed by running the following command.
```bash
python -m pip install git+https://github.com/HelixirLabs/helixir-api-client
```

Or using the PyPI packages repository (not yet available).

```bash
pip install helixirapi
```

## Features

- Currently, there are **42 methods**:
    - 35 api methods
    - 2 composed methods
    - 5 plotting methods
- **Translation of the date** from human readable to timestamp.
- **Translation of the symbol** to the contract.
- **Validation of parameter values** (prevents invalid queries).
- Automatic **iteration of queries** when a long time interval is requested.
- Defined **default values** for the option to omit parameter entry.
- And other useful features.


## Usage
[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://github.com/HelixirLabs/helixir-api-client/examples/Example.ipynb)

Getting data is as simple as calling one method!

After installing and importing the library, you need to create a _client instance_. Your authentication token is needed for this.
You can get it [here](TBA-TODO).

Then you can call any of the available methods.
Look at the two simple examples below.

### Get Token Info
```python
from helixirapi.helixir_api import HelixirApi

# Create client instance
AUTH_TOKEN = "Your_API_token"
client = HelixirApi(auth_token=AUTH_TOKEN)

client.get_token(contract="0x3EE2200Efb3400fAbB9AacF31297cBdD1d435D47")
```

<details>
<summary>Look at the output!</summary>

```
TokenResponse(
	name = Cardano Token,
	symbol = ADA,
	chain = BSC,
	decimals = 18.0,
	total_supply = 280000000.0,
	circulating_supply = 279993957.59734946,
	contract = 0x3EE2200Efb3400fAbB9AacF31297cBdD1d435D47,
)
```
</details>

### Get Prices of the Token
```python
client.get_candles(
    symbol="ada",
    from_="2022-01-01",
    to="2022-01-05",
    resolution="D1",
)
```

<details>
<summary>Look at the output!</summary>

```
[TokenPriceResponse(
 	time = 2021-12-31 00:00:00+00:00,
 	open = 1.3519262223018684,
 	high = 1.3812944903325324,
 	low = 1.2825855912353177,
 	close = 1.3117495628222282,
 ), TokenPriceResponse(
 	time = 2022-01-01 00:00:00+00:00,
 	open = 1.31175497388127,
 	high = 1.3722737725220566,
 	low = 1.311355140603232,
 	close = 1.371954964715582,
 ), TokenPriceResponse(
 	time = 2022-01-02 00:00:00+00:00,
 	open = 1.3718519000123486,
 	high = 1.3879185193567507,
 	low = 1.3469761448201745,
 	close = 1.3770684350522369,
 ), TokenPriceResponse(
 	time = 2022-01-03 00:00:00+00:00,
 	open = 1.3771325533135665,
 	high = 1.377167311599185,
 	low = 1.311636015481185,
 	close = 1.3171815488561158,
 )]
```
</details>


See the [examples folder](examples) for more details.
Or read some article on [Medium](https://medium.com/).

## License
[![License](https://img.shields.io/badge/License-Apache_2.0-yellow.svg)](LICENSE)

This package is licensed under the [Apache 2.0](LICENSE), so it is open source.

-------------------------------------------

[![](https://img.shields.io/badge/back%20to%20top-%E2%86%A9-blue)](#helixir-api-client)
