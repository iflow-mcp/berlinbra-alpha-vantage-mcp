from typing import Any, List, Dict, Optional
import asyncio
import httpx
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
import os

# Import functions from tools.py
from .tools import (
    make_alpha_request,
    format_quote,
    format_company_info,
    format_crypto_rate,
    format_time_series,
    format_historical_options,
    format_crypto_time_series,
    format_earnings_calendar,
    format_historical_earnings,
    ALPHA_VANTAGE_BASE,
    API_KEY
)

if not API_KEY:
    raise ValueError("Missing ALPHA_VANTAGE_API_KEY environment variable")

server = Server("alpha_vantage_finance")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """
    return [
        types.Tool(
            name="get-stock-quote",
            description="Get current stock quote information",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock symbol (e.g., AAPL, MSFT)",
                    },
                },
                "required": ["symbol"],
            },
        ),
        types.Tool(
            name="get-company-info",
            description="Get detailed company information",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock symbol (e.g., AAPL, MSFT)",
                    },
                },
                "required": ["symbol"],
            },
        ),
        types.Tool(
            name="get-crypto-exchange-rate",
            description="Get current cryptocurrency exchange rate",
            inputSchema={
                "type": "object",
                "properties": {
                    "crypto_symbol": {
                        "type": "string",
                        "description": "Cryptocurrency symbol (e.g., BTC, ETH)",
                    },
                    "market": {
                        "type": "string",
                        "description": "Market currency (e.g., USD, EUR)",
                        "default": "USD"
                    }
                },
                "required": ["crypto_symbol"],
            },
        ),
        types.Tool(
            name="get-time-series",
            description="Get daily time series data for a stock with optional date filtering",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock symbol (e.g., AAPL, MSFT)",
                    },
                    "outputsize": {
                        "type": "string",
                        "description": "compact (latest 100 data points) or full (up to 20 years of data). When start_date or end_date is specified, defaults to 'full'",
                        "enum": ["compact", "full"],
                        "default": "compact"
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Optional: Start date in YYYY-MM-DD format for filtering results",
                        "pattern": "^20[0-9]{2}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12][0-9]|3[01])$"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "Optional: End date in YYYY-MM-DD format for filtering results",
                        "pattern": "^20[0-9]{2}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12][0-9]|3[01])$"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Optional: Number of data points to return when no date filtering is applied (default: 5)",
                        "default": 5,
                        "minimum": 1
                    }
                },
                "required": ["symbol"],
            },
        ),
        types.Tool(
            name="get-historical-options",
            description="Get historical options chain data for a stock with advanced filtering and sorting capabilities",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock symbol (e.g., AAPL, MSFT)",
                    },
                    "date": {
                        "type": "string",
                        "description": "Optional: Trading date in YYYY-MM-DD format (defaults to previous trading day, must be after 2008-01-01)",
                        "pattern": "^20[0-9]{2}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12][0-9]|3[01])$"
                    },
                    "expiry_date": {
                        "type": "string",
                        "description": "Optional: Filter by expiration date in YYYY-MM-DD format",
                        "pattern": "^20[0-9]{2}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12][0-9]|3[01])$"
                    },
                    "min_strike": {
                        "type": "number",
                        "description": "Optional: Minimum strike price filter (e.g., 100.00)",
                        "minimum": 0
                    },
                    "max_strike": {
                        "type": "number",
                        "description": "Optional: Maximum strike price filter (e.g., 200.00)",
                        "minimum": 0
                    },
                    "contract_id": {
                        "type": "string",
                        "description": "Optional: Filter by specific contract ID (e.g., MSTR260116C00000500)"
                    },
                    "contract_type": {
                        "type": "string",
                        "description": "Optional: Filter by contract type (call or put)",
                        "enum": ["call", "put", "C", "P"]
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Optional: Number of contracts to return after filtering (default: 10, use -1 for all contracts)",
                        "default": 10,
                        "minimum": -1
                    },
                    "sort_by": {
                        "type": "string",
                        "description": "Optional: Field to sort by",
                        "enum": [
                            "strike",
                            "expiration",
                            "volume",
                            "open_interest",
                            "implied_volatility",
                            "delta",
                            "gamma",
                            "theta",
                            "vega",
                            "rho",
                            "last",
                            "bid",
                            "ask"
                        ],
                        "default": "strike"
                    },
                    "sort_order": {
                        "type": "string",
                        "description": "Optional: Sort order",
                        "enum": ["asc", "desc"],
                        "default": "asc"
                    }
                },
                "required": ["symbol"],
            },
        ),
        types.Tool(
            name="get-crypto-daily",
            description="Get daily time series data for a cryptocurrency",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Cryptocurrency symbol (e.g., BTC, ETH)",
                    },
                    "market": {
                        "type": "string",
                        "description": "Market currency (e.g., USD, EUR)",
                        "default": "USD"
                    }
                },
                "required": ["symbol"],
            },
        ),
        types.Tool(
            name="get-crypto-weekly",
            description="Get weekly time series data for a cryptocurrency",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Cryptocurrency symbol (e.g., BTC, ETH)",
                    },
                    "market": {
                        "type": "string",
                        "description": "Market currency (e.g., USD, EUR)",
                        "default": "USD"
                    }
                },
                "required": ["symbol"],
            },
        ),
        types.Tool(
            name="get-crypto-monthly",
            description="Get monthly time series data for a cryptocurrency",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Cryptocurrency symbol (e.g., BTC, ETH)",
                    },
                    "market": {
                        "type": "string",
                        "description": "Market currency (e.g., USD, EUR)",
                        "default": "USD"
                    }
                },
                "required": ["symbol"],
            },
        ),
        types.Tool(
            name="get-earnings-calendar",
            description="Get upcoming earnings calendar data for companies",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Optional: Stock symbol to filter earnings for a specific company (e.g., AAPL, MSFT, IBM)"
                    },
                    "horizon": {
                        "type": "string",
                        "description": "Optional: Time horizon for earnings data (3month, 6month, or 12month)",
                        "enum": ["3month", "6month", "12month"],
                        "default": "12month"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Optional: Number of earnings entries to return (default: 20)",
                        "default": 20,
                        "minimum": 1
                    }
                },
                "required": [],
            },
        ),
        types.Tool(
            name="get-historical-earnings",
            description="Get historical earnings data for a specific company",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "Stock symbol for the company (e.g., AAPL, MSFT, IBM)"
                    },
                    "limit_annual": {
                        "type": "integer",
                        "description": "Optional: Number of annual earnings to return (default: 5)",
                        "default": 5,
                        "minimum": 1
                    },
                    "limit_quarterly": {
                        "type": "integer",
                        "description": "Optional: Number of quarterly earnings to return (default: 8)",
                        "default": 8,
                        "minimum": 1
                    }
                },
                "required": ["symbol"],
            },
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle tool execution requests.
    Tools can fetch financial data and notify clients of changes.
    """
    if not arguments:
        return [types.TextContent(type="text", text="Missing arguments for the request")]

    if name == "get-stock-quote":
        symbol = arguments.get("symbol")
        if not symbol:
            return [types.TextContent(type="text", text="Missing symbol parameter")]

        symbol = symbol.upper()

        async with httpx.AsyncClient() as client:
            quote_data = await make_alpha_request(
                client,
                "GLOBAL_QUOTE",
                symbol
            )

            if isinstance(quote_data, str):
                return [types.TextContent(type="text", text=f"Error: {quote_data}")]

            formatted_quote = format_quote(quote_data)
            quote_text = f"Stock quote for {symbol}:\n\n{formatted_quote}"

            return [types.TextContent(type="text", text=quote_text)]

    elif name == "get-company-info":
        symbol = arguments.get("symbol")
        if not symbol:
            return [types.TextContent(type="text", text="Missing symbol parameter")]

        symbol = symbol.upper()

        async with httpx.AsyncClient() as client:
            company_data = await make_alpha_request(
                client,
                "OVERVIEW",
                symbol
            )

            if isinstance(company_data, str):
                return [types.TextContent(type="text", text=f"Error: {company_data}")]

            formatted_info = format_company_info(company_data)
            info_text = f"Company information for {symbol}:\n\n{formatted_info}"

            return [types.TextContent(type="text", text=info_text)]

    elif name == "get-crypto-exchange-rate":
        crypto_symbol = arguments.get("crypto_symbol")
        if not crypto_symbol:
            return [types.TextContent(type="text", text="Missing crypto_symbol parameter")]

        market = arguments.get("market", "USD")
        crypto_symbol = crypto_symbol.upper()
        market = market.upper()

        async with httpx.AsyncClient() as client:
            crypto_data = await make_alpha_request(
                client,
                "CURRENCY_EXCHANGE_RATE",
                None,
                {
                    "from_currency": crypto_symbol,
                    "to_currency": market
                }
            )

            if isinstance(crypto_data, str):
                return [types.TextContent(type="text", text=f"Error: {crypto_data}")]

            formatted_rate = format_crypto_rate(crypto_data)
            rate_text = f"Cryptocurrency exchange rate for {crypto_symbol}/{market}:\n\n{formatted_rate}"

            return [types.TextContent(type="text", text=rate_text)]

    elif name == "get-time-series":
        symbol = arguments.get("symbol")
        if not symbol:
            return [types.TextContent(type="text", text="Missing symbol parameter")]

        symbol = symbol.upper()
        start_date = arguments.get("start_date")
        end_date = arguments.get("end_date")
        limit = arguments.get("limit", 5)
        
        # Auto-select outputsize: use 'full' when date filtering is requested
        outputsize = arguments.get("outputsize")
        if not outputsize:
            outputsize = "full" if (start_date or end_date) else "compact"

        async with httpx.AsyncClient() as client:
            time_series_data = await make_alpha_request(
                client,
                "TIME_SERIES_DAILY",
                symbol,
                {"outputsize": outputsize}
            )

            if isinstance(time_series_data, str):
                return [types.TextContent(type="text", text=f"Error: {time_series_data}")]

            formatted_series = format_time_series(time_series_data, start_date, end_date, limit)
            series_text = f"Time series data for {symbol}:\n\n{formatted_series}"

            return [types.TextContent(type="text", text=series_text)]

    elif name == "get-historical-options":
        symbol = arguments.get("symbol")
        date = arguments.get("date")
        expiry_date = arguments.get("expiry_date")
        min_strike = arguments.get("min_strike")
        max_strike = arguments.get("max_strike")
        contract_id = arguments.get("contract_id")
        contract_type = arguments.get("contract_type")
        limit = arguments.get("limit", 10)
        sort_by = arguments.get("sort_by", "strike")
        sort_order = arguments.get("sort_order", "asc")

        if not symbol:
            return [types.TextContent(type="text", text="Missing symbol parameter")]

        symbol = symbol.upper()

        async with httpx.AsyncClient() as client:
            params = {}
            if date:
                params["date"] = date

            options_data = await make_alpha_request(
                client,
                "HISTORICAL_OPTIONS",
                symbol,
                params
            )

            if isinstance(options_data, str):
                return [types.TextContent(type="text", text=f"Error: {options_data}")]

            formatted_options = format_historical_options(
                options_data, 
                limit, 
                sort_by, 
                sort_order,
                expiry_date,
                min_strike,
                max_strike,
                contract_id,
                contract_type
            )
            options_text = f"Historical options data for {symbol}"
            if date:
                options_text += f" on {date}"
            options_text += f":\n\n{formatted_options}"

            return [types.TextContent(type="text", text=options_text)]
            
    elif name == "get-crypto-daily":
        symbol = arguments.get("symbol")
        market = arguments.get("market", "USD")
        
        if not symbol:
            return [types.TextContent(type="text", text="Missing symbol parameter")]

        symbol = symbol.upper()
        market = market.upper()

        async with httpx.AsyncClient() as client:
            crypto_data = await make_alpha_request(
                client,
                "DIGITAL_CURRENCY_DAILY",
                symbol,
                {"market": market}
            )

            if isinstance(crypto_data, str):
                return [types.TextContent(type="text", text=f"Error: {crypto_data}")]

            formatted_data = format_crypto_time_series(crypto_data, "daily")
            data_text = f"Daily cryptocurrency time series for {symbol} in {market}:\n\n{formatted_data}"

            return [types.TextContent(type="text", text=data_text)]
            
    elif name == "get-crypto-weekly":
        symbol = arguments.get("symbol")
        market = arguments.get("market", "USD")
        
        if not symbol:
            return [types.TextContent(type="text", text="Missing symbol parameter")]

        symbol = symbol.upper()
        market = market.upper()

        async with httpx.AsyncClient() as client:
            crypto_data = await make_alpha_request(
                client,
                "DIGITAL_CURRENCY_WEEKLY",
                symbol,
                {"market": market}
            )

            if isinstance(crypto_data, str):
                return [types.TextContent(type="text", text=f"Error: {crypto_data}")]

            formatted_data = format_crypto_time_series(crypto_data, "weekly")
            data_text = f"Weekly cryptocurrency time series for {symbol} in {market}:\n\n{formatted_data}"

            return [types.TextContent(type="text", text=data_text)]
            
    elif name == "get-crypto-monthly":
        symbol = arguments.get("symbol")
        market = arguments.get("market", "USD")
        
        if not symbol:
            return [types.TextContent(type="text", text="Missing symbol parameter")]

        symbol = symbol.upper()
        market = market.upper()

        async with httpx.AsyncClient() as client:
            crypto_data = await make_alpha_request(
                client,
                "DIGITAL_CURRENCY_MONTHLY",
                symbol,
                {"market": market}
            )

            if isinstance(crypto_data, str):
                return [types.TextContent(type="text", text=f"Error: {crypto_data}")]

            formatted_data = format_crypto_time_series(crypto_data, "monthly")
            data_text = f"Monthly cryptocurrency time series for {symbol} in {market}:\n\n{formatted_data}"

            return [types.TextContent(type="text", text=data_text)]
            
    elif name == "get-earnings-calendar":
        symbol = arguments.get("symbol")
        horizon = arguments.get("horizon", "12month")
        limit = arguments.get("limit", 20)
        
        async with httpx.AsyncClient() as client:
            params = {"horizon": horizon}
            if symbol:
                params["symbol"] = symbol.upper()
                
            earnings_data = await make_alpha_request(
                client,
                "EARNINGS_CALENDAR",
                None,
                params
            )

            if isinstance(earnings_data, str):
                return [types.TextContent(type="text", text=f"Error: {earnings_data}")]

            formatted_earnings = format_earnings_calendar(earnings_data, limit)
            earnings_text = f"Earnings calendar"
            if symbol:
                earnings_text += f" for {symbol.upper()}"
            if horizon:
                earnings_text += f" ({horizon})"
            earnings_text += f":\n\n{formatted_earnings}"

            return [types.TextContent(type="text", text=earnings_text)]
            
    elif name == "get-historical-earnings":
        symbol = arguments.get("symbol")
        limit_annual = arguments.get("limit_annual", 5)
        limit_quarterly = arguments.get("limit_quarterly", 8)
        
        if not symbol:
            return [types.TextContent(type="text", text="Missing symbol parameter")]

        symbol = symbol.upper()

        async with httpx.AsyncClient() as client:
            earnings_data = await make_alpha_request(
                client,
                "EARNINGS",
                symbol
            )

            if isinstance(earnings_data, str):
                return [types.TextContent(type="text", text=f"Error: {earnings_data}")]

            formatted_earnings = format_historical_earnings(earnings_data, limit_annual, limit_quarterly)
            earnings_text = f"Historical earnings for {symbol}:\n\n{formatted_earnings}"

            return [types.TextContent(type="text", text=earnings_text)]
    else:
        return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="alpha_vantage_finance",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

# This is needed if you'd like to connect to a custom client
if __name__ == "__main__":
    asyncio.run(main())
