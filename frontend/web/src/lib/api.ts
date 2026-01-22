
/**
 * Smart API Client with Failover Strategy
 * Primary: AWS EC2 (VITE_AWS_API_URL)
 * Fallback: Render.com (VITE_RENDER_API_URL)
 */

const AWS_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const RENDER_URL = process.env.NEXT_PUBLIC_RENDER_API_URL || '';

let currentBaseUrl = AWS_URL;

/**
 * Check if the primary server is alive.
 * If not, switch to fallback.
 */
async function getHealthyBaseUrl(): Promise<string> {
    // Optimization: If we already switched to fallback recently, maybe stick to it?
    // For now, always try Primary first unless marked bad? 
    // Simple approach: Try Primary. If fetch throws network error, try Secondary.
    return currentBaseUrl;
}

export async function fetchWithFailover(endpoint: string, options: RequestInit = {}): Promise<Response> {
    const url = `${currentBaseUrl}${endpoint}`;

    try {
        console.log(`[API] Requesting: ${url}`);
        const res = await fetch(url, options);

        // If 5xx error, maybe failover? For now, only failover on NETWORK error (catch block)
        return res;

    } catch (err) {
        console.warn(`[API] Primary (${currentBaseUrl}) failed. Checking fallback...`, err);

        if (currentBaseUrl === AWS_URL && RENDER_URL) {
            console.log(`[API] Switching to Fallback: ${RENDER_URL}`);
            currentBaseUrl = RENDER_URL; // Permanent switch for this session
            const fallbackUrl = `${currentBaseUrl}${endpoint}`;
            return fetch(fallbackUrl, options);
        }

        throw err;
    }
}

/**
 * AI Brain Service Endpoints
 * Strategic thinking and analysis capabilities
 */
export const brainEndpoints = {
    entryAnalysis: '/api/v1/brain/entry-analysis',
    riskAssessment: '/api/v1/brain/risk-assessment',
    regimeDetection: '/api/v1/brain/regime-detection',
    portfolioRebalance: '/api/v1/brain/portfolio-rebalance',
    earningsPlay: '/api/v1/brain/earnings-play',
    memory: '/api/v1/brain/memory',
    health: '/api/v1/brain/health'
} as const;

/**
 * Market Data Service Endpoints
 */
export const marketEndpoints = {
    quote: (symbol: string) => `/api/v1/market/quote/${symbol}`,
    ohlcv: (symbol: string) => `/api/v1/market/ohlcv/${symbol}`,
    health: '/api/v1/market/health'
} as const;

/**
 * Scanner Service Endpoints
 */
export const scannerEndpoints = {
    templates: '/api/v1/scan/templates',
    symbols: '/api/v1/scan/symbols',
    preview: '/api/v1/scan/preview',
    execute: '/api/v1/scan/execute'
} as const;

/**
 * Helper to call brain endpoints with proper typing
 */
export async function callBrainAPI<T>(
    endpoint: keyof typeof brainEndpoints | string,
    payload: Record<string, unknown>
): Promise<T> {
    const url = typeof endpoint === 'string' && endpoint.startsWith('/')
        ? endpoint
        : brainEndpoints[endpoint as keyof typeof brainEndpoints];

    const res = await fetchWithFailover(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    if (!res.ok) {
        throw new Error(`Brain API error: ${res.status} ${res.statusText}`);
    }

    return res.json();
}

