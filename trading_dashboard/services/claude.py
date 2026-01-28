"""
Claude LLM Service via AWS Bedrock
Provides AI-powered market analysis and trade reasoning
"""
import os
import json
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ClaudeConfig:
    """AWS Bedrock configuration for Claude"""
    region: str
    access_key: str
    secret_key: str
    model_id: str = "anthropic.claude-3-haiku-20240307-v1:0"
    
    @classmethod
    def from_env(cls) -> Optional["ClaudeConfig"]:
        """Load config from environment, returns None if not configured"""
        region = os.environ.get("AWS_REGION")
        access_key = os.environ.get("AWS_ACCESS_KEY_ID")
        secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
        
        if not all([region, access_key, secret_key]):
            return None
        
        return cls(
            region=region,
            access_key=access_key,
            secret_key=secret_key
        )


class ClaudeService:
    """
    Claude LLM service for enhanced trading analysis.
    
    Features:
    - Market brief generation
    - Trade reasoning explanation
    - Risk assessment
    """
    
    def __init__(self, config: Optional[ClaudeConfig] = None):
        self.config = config
        self.client = None
        self.enabled = False
        
        if config:
            try:
                import boto3
                self.client = boto3.client(
                    "bedrock-runtime",
                    region_name=config.region,
                    aws_access_key_id=config.access_key,
                    aws_secret_access_key=config.secret_key
                )
                self.enabled = True
                logger.info("Claude service initialized via AWS Bedrock")
            except Exception as e:
                logger.warning(f"Claude service unavailable: {e}")
                self.enabled = False
    
    def _invoke(self, prompt: str, max_tokens: int = 500) -> Optional[str]:
        """Invoke Claude via Bedrock"""
        if not self.enabled or not self.client:
            return None
        
        try:
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            })
            
            response = self.client.invoke_model(
                modelId=self.config.model_id,
                body=body,
                contentType="application/json",
                accept="application/json"
            )
            
            result = json.loads(response["body"].read())
            return result["content"][0]["text"]
        except Exception as e:
            logger.error(f"Claude invocation failed: {e}")
            return None
    
    def generate_market_brief(
        self,
        coin: str,
        price: float,
        change_24h: float,
        signal: str,
        confidence: float,
        regime: str,
        btc_dominance: float,
        market_sentiment: str,
        reasoning: list
    ) -> str:
        """
        Generate a concise market brief using Claude.
        
        Returns a 2-3 sentence summary of current market conditions.
        """
        if not self.enabled:
            return self._fallback_brief(coin, signal, confidence, regime)
        
        prompt = f"""You are a crypto trading analyst. Generate a brief 2-3 sentence market summary.

Current data for {coin}/USDT:
- Price: ${price:,.2f} ({change_24h:+.2f}% 24h)
- AI Signal: {signal} (Confidence: {confidence:.0%})
- Market Regime: {regime}
- BTC Dominance: {btc_dominance:.1f}%
- Global Sentiment: {market_sentiment}
- Key factors: {'; '.join(reasoning[:3])}

Write a concise, professional market brief. No bullet points. Be direct."""

        result = self._invoke(prompt, max_tokens=150)
        return result if result else self._fallback_brief(coin, signal, confidence, regime)
    
    def explain_signal(
        self,
        coin: str,
        signal: str,
        confidence: float,
        indicators: Dict[str, Any],
        reasoning: list
    ) -> str:
        """
        Generate a detailed explanation of why the AI suggested this signal.
        """
        if not self.enabled:
            return self._fallback_explanation(signal, reasoning)
        
        prompt = f"""You are a crypto trading analyst explaining an AI trading signal.

Signal: {signal} for {coin}/USDT
Confidence: {confidence:.0%}

Technical Indicators:
- RSI: {indicators.get('rsi', 'N/A')}
- Price Position (24h range): {indicators.get('price_position_pct', 'N/A')}%
- Volatility: {indicators.get('volatility_pct', 'N/A')}%
- 24h Change: {indicators.get('price_change_24h', 'N/A')}%
- BTC Dominance: {indicators.get('btc_dominance', 'N/A')}%
- Market Sentiment: {indicators.get('market_sentiment', 'N/A')}

AI Reasoning:
{chr(10).join(f'- {r}' for r in reasoning)}

Explain in 3-4 sentences why this signal was generated. Be specific about which factors were most important."""

        result = self._invoke(prompt, max_tokens=250)
        return result if result else self._fallback_explanation(signal, reasoning)
    
    def assess_risk(
        self,
        coin: str,
        signal: str,
        position_size_usdt: float,
        leverage: int,
        volatility: float,
        balance: float
    ) -> Dict[str, Any]:
        """
        Assess the risk of a potential trade.
        Risk is based on MARGIN (position_size / leverage), not position size.
        """
        margin_usdt = position_size_usdt / leverage
        risk_pct = (margin_usdt / balance) * 100 if balance > 0 else 100
        
        # Determine risk level based on margin % of balance
        if risk_pct > 10 or volatility > 5:
            level = "HIGH"
        elif risk_pct > 5 or volatility > 3:
            level = "MEDIUM"
        else:
            level = "LOW"
        
        if not self.enabled:
            return self._fallback_risk(risk_pct, margin_usdt, balance, volatility, leverage)
        
        prompt = f"""You are a risk management advisor for crypto trading.

Proposed Trade:
- Asset: {coin}/USDT
- Direction: {signal}
- Position Size: ${position_size_usdt:.2f}
- Leverage: {leverage}x
- Margin (actual risk): ${margin_usdt:.2f}
- Account Balance: ${balance:.2f}
- Margin as % of Balance: {risk_pct:.1f}%
- Current Volatility: {volatility:.2f}%

Provide a brief risk assessment (1-2 sentences). Be specific about the margin amount and risk level."""

        result = self._invoke(prompt, max_tokens=150)
        
        return {
            "level": level,
            "risk_pct": round(risk_pct, 1),
            "assessment": result if result else f"${margin_usdt:.2f} margin ({risk_pct:.1f}% of balance) at {leverage}x. {'Acceptable' if level == 'LOW' else 'Caution advised' if level == 'MEDIUM' else 'High risk'}."
        }
    
    def generate_trade_journal(
        self,
        coin: str,
        action: str,
        side: str,
        size: float,
        price: float,
        signal: str,
        confidence: float,
        reasoning: list
    ) -> str:
        """
        Generate a trade journal entry for record-keeping.
        """
        if not self.enabled:
            return f"{action} {side} {size} {coin} at ${price:,.2f}. AI signal: {signal} ({confidence:.0%})"
        
        prompt = f"""Write a brief trade journal entry (1-2 sentences) for this trade:

Action: {action} {side}
Asset: {coin}/USDT
Size: {size}
Price: ${price:,.2f}
AI Signal: {signal} ({confidence:.0%})
Key Reason: {reasoning[0] if reasoning else 'Market conditions'}

Be concise and professional. Include the key reasoning."""

        result = self._invoke(prompt, max_tokens=100)
        return result if result else f"{action} {side} {size} {coin} at ${price:,.2f}. AI signal: {signal} ({confidence:.0%})"
    
    def _fallback_brief(self, coin: str, signal: str, confidence: float, regime: str) -> str:
        """Fallback when Claude is unavailable"""
        return f"{coin} is in a {regime.lower().replace('_', ' ')} market. AI suggests {signal} with {confidence:.0%} confidence."
    
    def _fallback_explanation(self, signal: str, reasoning: list) -> str:
        """Fallback explanation when Claude is unavailable"""
        return f"The AI generated a {signal} signal based on: {'; '.join(reasoning[:3])}"
    
    def _fallback_risk(self, risk_pct: float, margin_usdt: float, balance: float, volatility: float, leverage: int) -> Dict[str, Any]:
        """Fallback risk assessment"""
        if risk_pct > 10 or volatility > 5:
            level = "HIGH"
            assessment = f"High risk: ${margin_usdt:.2f} margin is {risk_pct:.1f}% of your ${balance:.0f} balance."
        elif risk_pct > 5 or volatility > 3:
            level = "MEDIUM"
            assessment = f"Moderate risk: ${margin_usdt:.2f} margin ({risk_pct:.1f}% of balance) at {leverage}x."
        else:
            level = "LOW"
            assessment = f"Low risk: ${margin_usdt:.2f} margin is only {risk_pct:.1f}% of your balance."
        
        return {"level": level, "risk_pct": risk_pct, "assessment": assessment}
    
    def chat(self, message: str, context: Dict[str, Any], history: list = None) -> str:
        """
        Context-aware chat with the AI advisor.
        
        Context includes:
        - coin: Current trading pair
        - price: Current price
        - change_24h: 24h price change
        - signal: Current AI signal
        - confidence: Signal confidence
        - regime: Market regime
        - position: Current position (if any)
        - balance: Account balance
        - btc_dominance: BTC market dominance
        - market_sentiment: Global sentiment
        - trending_coins: Currently trending
        
        History is a list of {"role": "user"|"assistant", "content": "..."} dicts
        """
        if not self.enabled:
            return self._fallback_chat(message, context)
        
        # Build context string
        ctx_parts = []
        ctx_parts.append(f"Current coin: {context.get('coin', 'BTC')}/USDT")
        ctx_parts.append(f"Price: ${context.get('price', 0):,.2f} ({context.get('change_24h', 0):+.2f}% 24h)")
        ctx_parts.append(f"AI Signal: {context.get('signal', 'NEUTRAL')} ({context.get('confidence', 0):.0%} confidence)")
        ctx_parts.append(f"Market Regime: {context.get('regime', 'UNKNOWN')}")
        ctx_parts.append(f"Account Balance: ${context.get('balance', 0):,.2f}")
        
        # Position info
        pos = context.get('position')
        if pos and pos.get('size'):
            ctx_parts.append(f"Open Position: {pos.get('side')} {pos.get('size')} @ ${pos.get('entry_price', 0):,.2f} (P&L: ${pos.get('pnl', 0):,.2f})")
        else:
            ctx_parts.append("Open Position: None")
        
        # Global market
        ctx_parts.append(f"BTC Dominance: {context.get('btc_dominance', 0):.1f}%")
        ctx_parts.append(f"Market Sentiment: {context.get('market_sentiment', 'UNKNOWN')}")
        if context.get('trending_coins'):
            ctx_parts.append(f"Trending: {', '.join(context.get('trending_coins', [])[:5])}")
        
        context_str = "\n".join(ctx_parts)
        
        # Build conversation history string
        history_str = ""
        if history and len(history) > 0:
            history_parts = []
            for msg in history[-6:]:  # Keep last 6 messages (3 exchanges)
                role = "User" if msg.get("role") == "user" else "You"
                history_parts.append(f"{role}: {msg.get('content', '')}")
            history_str = "\n\nCONVERSATION HISTORY:\n" + "\n".join(history_parts)
        
        prompt = f"""You are an AI trading advisor for RegimeForge Alpha, a crypto trading dashboard on WEEX exchange.

CURRENT MARKET CONTEXT:
{context_str}{history_str}

USER MESSAGE: {message}

Respond as a helpful trading advisor. Be concise (2-4 sentences unless more detail is needed).
- If asked about positions, use the context above
- If asked for trade advice, consider the AI signal and market conditions
- If asked about risk, factor in balance and position size
- Be direct and actionable
- Use trading terminology appropriately
- If you don't have enough info, say so
- IMPORTANT: Stay consistent with any advice you gave in the conversation history

Respond naturally as a trading assistant:"""

        result = self._invoke(prompt, max_tokens=400)
        return result if result else self._fallback_chat(message, context)
    
    def _fallback_chat(self, message: str, context: Dict[str, Any]) -> str:
        """Fallback when Claude is unavailable"""
        msg_lower = message.lower()
        
        if 'position' in msg_lower:
            pos = context.get('position')
            if pos and pos.get('size'):
                return f"You have a {pos.get('side')} position of {pos.get('size')} {context.get('coin', 'BTC')} at ${pos.get('entry_price', 0):,.2f}. Current P&L: ${pos.get('pnl', 0):,.2f}."
            return "You don't have any open position on this coin."
        
        if 'signal' in msg_lower or 'recommend' in msg_lower:
            return f"Current AI signal is {context.get('signal', 'NEUTRAL')} with {context.get('confidence', 0):.0%} confidence. Market regime: {context.get('regime', 'UNKNOWN')}."
        
        if 'balance' in msg_lower:
            return f"Your available balance is ${context.get('balance', 0):,.2f} USDT."
        
        if 'trend' in msg_lower:
            trending = context.get('trending_coins', [])
            if trending:
                return f"Currently trending on CoinGecko: {', '.join(trending[:5])}. Market sentiment is {context.get('market_sentiment', 'NEUTRAL')}."
            return "Unable to fetch trending data right now."
        
        return f"I'm here to help with your trading. Current {context.get('coin', 'BTC')} price is ${context.get('price', 0):,.2f}. AI suggests {context.get('signal', 'NEUTRAL')}. What would you like to know?"
