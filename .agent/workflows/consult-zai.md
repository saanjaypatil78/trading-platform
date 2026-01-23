---
description: Consult z.ai expert team for domain-specific expertise
---

# /consult-zai Workflow

Use this workflow when you need specialized domain expertise for the trading platform.

## Quick Reference

| Need | Expert | Trigger |
|------|--------|---------|
| Trading strategy | Finance | "How should I detect..." |
| System architecture | Engineering | "What's the best way to structure..." |
| ML/signals | Data Science | "What features predict..." |
| Security/compliance | Security | "How do I secure..." |

## Steps

1. **Identify the domain** of your question
2. **Formulate a specific query** with context:
   - What you're building
   - Constraints (latency, scale, market)
   - What you've tried
3. **Consult z.ai** via the `zread` MCP server
4. **Review expert analysis**
5. **Let Antigravity implement** the recommendation

## Example Queries

```
Finance: "What orderflow patterns indicate institutional accumulation 
in Indian equities given 5% circuit limits?"

Engineering: "Best WebSocket reconnection strategy for L2 data where 
I can't miss more than 1 second of updates?"

Data Science: "What features from footprint data best predict 
short-term price reversals?"

Security: "How should I rotate broker API keys in production 
without downtime?"
```

## Configuration

✅ Already configured in `.antigravity/mcp-config.json`
✅ API key set: `Z_AI_API_KEY` environment variable
