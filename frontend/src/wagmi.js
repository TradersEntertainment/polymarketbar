import { getDefaultConfig } from '@rainbow-me/rainbowkit';
import { polygon } from 'wagmi/chains';

export const config = getDefaultConfig({
    appName: 'PolymarketCandles',
    projectId: 'YOUR_PROJECT_ID', // TODO: Get a real ID from WalletConnect Cloud
    chains: [polygon],
    ssr: false,
});
