"""
Alpha Vantage MCP Tools Module

This module contains utility functions for making requests to the Alpha Vantage API
and formatting the responses.
"""

from typing import Any, Dict, Optional, List
import httpx
import os
import csv
import io
from datetime import datetime

ALPHA_VANTAGE_BASE = "https://www.alphavantage.co/query"
API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY')

async def make_alpha_request(client: httpx.AsyncClient, function: str, symbol: Optional[str], additional_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any] | str:
    """Make a request to the Alpha Vantage API with proper error handling.
    
    Args:
        client: An httpx AsyncClient instance
        function: The Alpha Vantage API function to call
        symbol: The stock/crypto symbol (can be None for some endpoints)
        additional_params: Additional parameters to include in the request
        
    Returns:
        Either a dictionary containing the API response, or a string with an error message
    """
    params = {
        "function": function,
        "apikey": API_KEY
    }
    
    if symbol:
        params["symbol"] = symbol
        
    if additional_params:
        params.update(additional_params)

    try:
        response = await client.get(
            ALPHA_VANTAGE_BASE,
            params=params,
            timeout=30.0
        )

        # Check for specific error responses
        if response.status_code == 429:
            return f"Rate limit exceeded. Error details: {response.text}"
        elif response.status_code == 403:
            return f"API key invalid or expired. Error details: {response.text}"

        response.raise_for_status()

        # Check if response is empty
        if not response.text.strip():
            return "Empty response received from Alpha Vantage API"
        
        # Special handling for EARNINGS_CALENDAR which returns CSV by default
        if function == "EARNINGS_CALENDAR":
            try:
                # Parse CSV response
                csv_reader = csv.DictReader(io.StringIO(response.text))
                earnings_list = list(csv_reader)
                return earnings_list
            except Exception as e:
                return f"Error parsing CSV response: {str(e)}"
        
        # For other functions, expect JSON
        try:
            data = response.json()
        except ValueError as e:
            return f"Invalid JSON response from Alpha Vantage API: {response.text[:200]}"

        # Check for Alpha Vantage specific error messages
        if "Error Message" in data:
            return f"Alpha Vantage API error: {data['Error Message']}"
        if "Note" in data and "API call frequency" in data["Note"]:
            return f"Rate limit warning: {data['Note']}"

        return data
    except httpx.TimeoutException:
        return "Request timed out after 30 seconds. The Alpha Vantage API may be experiencing delays."
    except httpx.ConnectError:
        return "Failed to connect to Alpha Vantage API. Please check your internet connection."
    except httpx.HTTPStatusError as e:
        return f"HTTP error occurred: {str(e)} - Response: {e.response.text}"
    except Exception as e:
        return f"Unexpected error occurred: {str(e)}"


def format_quote(quote_data: Dict[str, Any]) -> str:
    """Format quote data into a concise string.
    
    Args:
        quote_data: The response data from the Alpha Vantage Global Quote endpoint
        
    Returns:
        A formatted string containing the quote information
    """
    try:
        global_quote = quote_data.get("Global Quote", {})
        if not global_quote:
            return "No quote data available in the response"

        return (
            f"Price: ${global_quote.get('05. price', 'N/A')}\n"
            f"Change: ${global_quote.get('09. change', 'N/A')} "
            f"({global_quote.get('10. change percent', 'N/A')})\n"
            f"Volume: {global_quote.get('06. volume', 'N/A')}\n"
            f"High: ${global_quote.get('03. high', 'N/A')}\n"
            f"Low: ${global_quote.get('04. low', 'N/A')}\n"
            "---"
        )
    except Exception as e:
        return f"Error formatting quote data: {str(e)}"


def format_company_info(overview_data: Dict[str, Any]) -> str:
    """Format company information into a concise string.
    
    Args:
        overview_data: The response data from the Alpha Vantage OVERVIEW endpoint
        
    Returns:
        A formatted string containing the company information
    """
    try:
        if not overview_data:
            return "No company information available in the response"

        return (
            f"Name: {overview_data.get('Name', 'N/A')}\n"
            f"Sector: {overview_data.get('Sector', 'N/A')}\n"
            f"Industry: {overview_data.get('Industry', 'N/A')}\n"
            f"Market Cap: ${overview_data.get('MarketCapitalization', 'N/A')}\n"
            f"Description: {overview_data.get('Description', 'N/A')}\n"
            f"Exchange: {overview_data.get('Exchange', 'N/A')}\n"
            f"Currency: {overview_data.get('Currency', 'N/A')}\n"
            "---"
        )
    except Exception as e:
        return f"Error formatting company data: {str(e)}"


def format_crypto_rate(crypto_data: Dict[str, Any]) -> str:
    """Format cryptocurrency exchange rate data into a concise string.
    
    Args:
        crypto_data: The response data from the Alpha Vantage CURRENCY_EXCHANGE_RATE endpoint
        
    Returns:
        A formatted string containing the cryptocurrency exchange rate information
    """
    try:
        realtime_data = crypto_data.get("Realtime Currency Exchange Rate", {})
        if not realtime_data:
            return "No exchange rate data available in the response"

        return (
            f"From: {realtime_data.get('2. From_Currency Name', 'N/A')} ({realtime_data.get('1. From_Currency Code', 'N/A')})\n"
            f"To: {realtime_data.get('4. To_Currency Name', 'N/A')} ({realtime_data.get('3. To_Currency Code', 'N/A')})\n"
            f"Exchange Rate: {realtime_data.get('5. Exchange Rate', 'N/A')}\n"
            f"Last Updated: {realtime_data.get('6. Last Refreshed', 'N/A')} {realtime_data.get('7. Time Zone', 'N/A')}\n"
            f"Bid Price: {realtime_data.get('8. Bid Price', 'N/A')}\n"
            f"Ask Price: {realtime_data.get('9. Ask Price', 'N/A')}\n"
            "---"
        )
    except Exception as e:
        return f"Error formatting cryptocurrency data: {str(e)}"


def format_time_series(time_series_data: Dict[str, Any], start_date: Optional[str] = None, end_date: Optional[str] = None, limit: int = 5) -> str:
    """Format time series data into a concise string with optional date filtering.
    
    Args:
        time_series_data: The response data from the Alpha Vantage TIME_SERIES_DAILY endpoint
        start_date: Optional start date in YYYY-MM-DD format for filtering
        end_date: Optional end date in YYYY-MM-DD format for filtering  
        limit: Number of data points to return when no date filtering is applied
        
    Returns:
        A formatted string containing the time series information
    """
    try:
        # Get the daily time series data
        time_series = time_series_data.get("Time Series (Daily)", {})
        if not time_series:
            return "No time series data available in the response"

        # Get metadata
        metadata = time_series_data.get("Meta Data", {})
        symbol = metadata.get("2. Symbol", "Unknown")
        last_refreshed = metadata.get("3. Last Refreshed", "Unknown")

        # Filter by date range if specified
        filtered_data = {}
        if start_date or end_date:
            for date_str, values in time_series.items():
                try:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                    
                    # Check start date filter
                    if start_date:
                        start_obj = datetime.strptime(start_date, "%Y-%m-%d")
                        if date_obj < start_obj:
                            continue
                    
                    # Check end date filter
                    if end_date:
                        end_obj = datetime.strptime(end_date, "%Y-%m-%d")
                        if date_obj > end_obj:
                            continue
                    
                    filtered_data[date_str] = values
                except ValueError:
                    # Skip invalid date formats
                    continue
            
            # Sort filtered data by date (most recent first)
            sorted_items = sorted(filtered_data.items(), key=lambda x: x[0], reverse=True)
        else:
            # Use original data with limit
            sorted_items = list(time_series.items())[:limit]

        if not sorted_items:
            return f"No time series data found for the specified date range"

        # Build header
        formatted_data = [
            f"Time Series Data for {symbol} (Last Refreshed: {last_refreshed})\n"
        ]
        
        # Add date range info if filtering was applied
        if start_date or end_date:
            date_range = ""
            if start_date and end_date:
                date_range = f"Date Range: {start_date} to {end_date}"
            elif start_date:
                date_range = f"From: {start_date}"
            elif end_date:
                date_range = f"Until: {end_date}"
            formatted_data.append(f"{date_range} ({len(sorted_items)} data points)\n\n")
        else:
            formatted_data.append(f"(Showing {len(sorted_items)} most recent data points)\n\n")

        # Format the data points
        for date, values in sorted_items:
            formatted_data.append(
                f"Date: {date}\n"
                f"Open: ${values.get('1. open', 'N/A')}\n"
                f"High: ${values.get('2. high', 'N/A')}\n"
                f"Low: ${values.get('3. low', 'N/A')}\n"
                f"Close: ${values.get('4. close', 'N/A')}\n"
                f"Volume: {values.get('5. volume', 'N/A')}\n"
                "---\n"
            )

        return "\n".join(formatted_data)
    except Exception as e:
        return f"Error formatting time series data: {str(e)}"


def format_crypto_time_series(time_series_data: Dict[str, Any], series_type: str) -> str:
    """Format cryptocurrency time series data into a concise string.
    
    Args:
        time_series_data: The response data from Alpha Vantage Digital Currency endpoints
        series_type: Type of time series (daily, weekly, monthly)
        
    Returns:
        A formatted string containing the cryptocurrency time series information
    """
    try:
        # Determine the time series key based on series_type
        time_series_key = ""
        if series_type == "daily":
            time_series_key = "Time Series (Digital Currency Daily)"
        elif series_type == "weekly":
            time_series_key = "Time Series (Digital Currency Weekly)"
        elif series_type == "monthly":
            time_series_key = "Time Series (Digital Currency Monthly)"
        else:
            return f"Unknown series type: {series_type}"
            
        # Get the time series data
        time_series = time_series_data.get(time_series_key, {})
        if not time_series:
            all_keys = ", ".join(time_series_data.keys())
            return f"No cryptocurrency time series data found with key: '{time_series_key}'.\nAvailable keys: {all_keys}"

        # Get metadata
        metadata = time_series_data.get("Meta Data", {})
        crypto_symbol = metadata.get("2. Digital Currency Code", "Unknown")
        crypto_name = metadata.get("3. Digital Currency Name", "Unknown")
        market = metadata.get("4. Market Code", "Unknown")
        market_name = metadata.get("5. Market Name", "Unknown")
        last_refreshed = metadata.get("6. Last Refreshed", "Unknown")
        time_zone = metadata.get("7. Time Zone", "Unknown")

        # Format the header
        formatted_data = [
            f"{series_type.capitalize()} Time Series for {crypto_name} ({crypto_symbol})",
            f"Market: {market_name} ({market})",
            f"Last Refreshed: {last_refreshed} {time_zone}",
            ""
        ]

        # Format the most recent 5 data points
        for date, values in list(time_series.items())[:5]:
            # Get price information - based on the API response, we now know the correct field names
            open_price = values.get("1. open", "N/A")
            high_price = values.get("2. high", "N/A")
            low_price = values.get("3. low", "N/A")
            close_price = values.get("4. close", "N/A")
            volume = values.get("5. volume", "N/A")
            
            formatted_data.append(f"Date: {date}")
            formatted_data.append(f"Open: {open_price} {market}")
            formatted_data.append(f"High: {high_price} {market}")
            formatted_data.append(f"Low: {low_price} {market}")
            formatted_data.append(f"Close: {close_price} {market}")
            formatted_data.append(f"Volume: {volume}")
            formatted_data.append("---")
        
        return "\n".join(formatted_data)
    except Exception as e:
        return f"Error formatting cryptocurrency time series data: {str(e)}"


def format_earnings_calendar(earnings_data: List[Dict[str, str]], limit: int = 20) -> str:
    """Format earnings calendar data into a concise string.
    
    Args:
        earnings_data: List of earnings records from the Alpha Vantage EARNINGS_CALENDAR endpoint (CSV format)
        limit: Number of earnings entries to display (default: 20)
        
    Returns:
        A formatted string containing the earnings calendar information
    """
    try:
        if not isinstance(earnings_data, list):
            return f"Unexpected data format: {type(earnings_data)}"
            
        if not earnings_data:
            return "No earnings calendar data available"

        formatted = ["Upcoming Earnings Calendar:\n\n"]
        
        # Display limited number of entries
        display_earnings = earnings_data[:limit] if limit > 0 else earnings_data
        
        for earning in display_earnings:
            symbol = earning.get('symbol', 'N/A')
            name = earning.get('name', 'N/A')
            report_date = earning.get('reportDate', 'N/A')
            fiscal_date = earning.get('fiscalDateEnding', 'N/A')
            estimate = earning.get('estimate', 'N/A')
            currency = earning.get('currency', 'N/A')
            
            formatted.append(f"Company: {symbol} - {name}\n")
            formatted.append(f"Report Date: {report_date}\n")
            formatted.append(f"Fiscal Date End: {fiscal_date}\n")
            
            # Format estimate nicely
            if estimate and estimate != 'N/A' and estimate.strip():
                try:
                    est_float = float(estimate)
                    formatted.append(f"Estimate: ${est_float:.2f} {currency}\n")
                except ValueError:
                    formatted.append(f"Estimate: {estimate} {currency}\n")
            else:
                formatted.append(f"Estimate: Not available\n")
            
            formatted.append("---\n")
        
        if limit > 0 and len(earnings_data) > limit:
            formatted.append(f"\n... and {len(earnings_data) - limit} more earnings reports")
            
        return "".join(formatted)
    except Exception as e:
        return f"Error formatting earnings calendar data: {str(e)}"


def format_historical_earnings(earnings_data: Dict[str, Any], limit_annual: int = 5, limit_quarterly: int = 8) -> str:
    """Format historical earnings data into a concise string.
    
    Args:
        earnings_data: The response data from the Alpha Vantage EARNINGS endpoint
        limit_annual: Number of annual earnings to display (default: 5)
        limit_quarterly: Number of quarterly earnings to display (default: 8)
        
    Returns:
        A formatted string containing the historical earnings information
    """
    try:
        if "Error Message" in earnings_data:
            return f"Error: {earnings_data['Error Message']}"

        symbol = earnings_data.get("symbol", "Unknown")
        formatted = [f"Historical Earnings for {symbol}:\n\n"]
        
        # Format Annual Earnings
        annual_earnings = earnings_data.get("annualEarnings", [])
        if annual_earnings:
            formatted.append("=== ANNUAL EARNINGS ===\n")
            display_annual = annual_earnings[:limit_annual] if limit_annual > 0 else annual_earnings
            
            for earning in display_annual:
                fiscal_date = earning.get("fiscalDateEnding", "N/A")
                reported_eps = earning.get("reportedEPS", "N/A")
                
                formatted.append(f"Fiscal Year End: {fiscal_date}\n")
                formatted.append(f"Reported EPS: ${reported_eps}\n")
                formatted.append("---\n")
            
            if limit_annual > 0 and len(annual_earnings) > limit_annual:
                formatted.append(f"... and {len(annual_earnings) - limit_annual} more annual reports\n")
            formatted.append("\n")
        
        # Format Quarterly Earnings
        quarterly_earnings = earnings_data.get("quarterlyEarnings", [])
        if quarterly_earnings:
            formatted.append("=== QUARTERLY EARNINGS ===\n")
            display_quarterly = quarterly_earnings[:limit_quarterly] if limit_quarterly > 0 else quarterly_earnings
            
            for earning in display_quarterly:
                fiscal_date = earning.get("fiscalDateEnding", "N/A")
                reported_date = earning.get("reportedDate", "N/A")
                reported_eps = earning.get("reportedEPS", "N/A")
                estimated_eps = earning.get("estimatedEPS", "N/A")
                surprise = earning.get("surprise", "N/A")
                surprise_pct = earning.get("surprisePercentage", "N/A")
                report_time = earning.get("reportTime", "N/A")
                
                formatted.append(f"Fiscal Quarter End: {fiscal_date}\n")
                formatted.append(f"Reported Date: {reported_date}\n")
                formatted.append(f"Reported EPS: ${reported_eps}\n")
                formatted.append(f"Estimated EPS: ${estimated_eps}\n")
                
                # Format surprise with proper handling
                if surprise != "N/A" and surprise_pct != "N/A":
                    try:
                        surprise_float = float(surprise)
                        surprise_pct_float = float(surprise_pct)
                        if surprise_float >= 0:
                            formatted.append(f"Surprise: +${surprise_float:.2f} (+{surprise_pct_float:.2f}%)\n")
                        else:
                            formatted.append(f"Surprise: ${surprise_float:.2f} ({surprise_pct_float:.2f}%)\n")
                    except ValueError:
                        formatted.append(f"Surprise: {surprise} ({surprise_pct}%)\n")
                else:
                    formatted.append(f"Surprise: {surprise} ({surprise_pct}%)\n")
                
                formatted.append(f"Report Time: {report_time}\n")
                formatted.append("---\n")
            
            if limit_quarterly > 0 and len(quarterly_earnings) > limit_quarterly:
                formatted.append(f"... and {len(quarterly_earnings) - limit_quarterly} more quarterly reports\n")
        
        if not annual_earnings and not quarterly_earnings:
            formatted.append("No historical earnings data available\n")
            
        return "".join(formatted)
    except Exception as e:
        return f"Error formatting historical earnings data: {str(e)}"


def format_historical_options(options_data: Dict[str, Any], limit: int = 10, sort_by: str = "strike", sort_order: str = "asc") -> str:
    """Format historical options chain data into a concise string with sorting.
    
    Args:
        options_data: The response data from the Alpha Vantage HISTORICAL_OPTIONS endpoint
        limit: Number of contracts to return (-1 for all)
        sort_by: Field to sort by
        sort_order: Sort order (asc or desc)
        
    Returns:
        A formatted string containing the historical options information
    """
    try:
        if "Error Message" in options_data:
            return f"Error: {options_data['Error Message']}"

        options_chain = options_data.get("data", [])

        if not options_chain:
            return "No options data available in the response"

        formatted = [
            f"Historical Options Data:\n",
            f"Status: {options_data.get('message', 'N/A')}\n",
            f"Sorted by: {sort_by} ({sort_order})\n\n"
        ]

        # Convert string values to float for numeric sorting
        def get_sort_key(contract):
            value = contract.get(sort_by, 0)
            try:
                # Remove $ and % signs if present
                if isinstance(value, str):
                    value = value.replace('$', '').replace('%', '')
                return float(value)
            except (ValueError, TypeError):
                return value

        # Sort the options chain
        sorted_chain = sorted(
            options_chain,
            key=get_sort_key,
            reverse=(sort_order == "desc")
        )

        # If limit is -1, show all contracts
        display_contracts = sorted_chain if limit == -1 else sorted_chain[:limit]

        for contract in display_contracts:
            formatted.append(f"Contract Details:\n")
            formatted.append(f"Contract ID: {contract.get('contractID', 'N/A')}\n")
            formatted.append(f"Expiration: {contract.get('expiration', 'N/A')}\n")
            formatted.append(f"Strike: ${contract.get('strike', 'N/A')}\n")
            formatted.append(f"Type: {contract.get('type', 'N/A')}\n")
            formatted.append(f"Last: ${contract.get('last', 'N/A')}\n")
            formatted.append(f"Mark: ${contract.get('mark', 'N/A')}\n")
            formatted.append(f"Bid: ${contract.get('bid', 'N/A')} (Size: {contract.get('bid_size', 'N/A')})\n")
            formatted.append(f"Ask: ${contract.get('ask', 'N/A')} (Size: {contract.get('ask_size', 'N/A')})\n")
            formatted.append(f"Volume: {contract.get('volume', 'N/A')}\n")
            formatted.append(f"Open Interest: {contract.get('open_interest', 'N/A')}\n")
            formatted.append(f"IV: {contract.get('implied_volatility', 'N/A')}\n")
            formatted.append(f"Delta: {contract.get('delta', 'N/A')}\n")
            formatted.append(f"Gamma: {contract.get('gamma', 'N/A')}\n")
            formatted.append(f"Theta: {contract.get('theta', 'N/A')}\n")
            formatted.append(f"Vega: {contract.get('vega', 'N/A')}\n")
            formatted.append(f"Rho: {contract.get('rho', 'N/A')}\n")
            formatted.append("---\n")

        if limit != -1 and len(sorted_chain) > limit:
            formatted.append(f"\n... and {len(sorted_chain) - limit} more contracts")

        return "".join(formatted)
    except Exception as e:
        return f"Error formatting options data: {str(e)}"
