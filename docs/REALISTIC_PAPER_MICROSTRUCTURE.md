# Realistic PAPER Microstructure Replay

Adds conservative execution realism on top of temporal replay.

## Models

- best bid / ask
- executable quantity
- multi-level order-book fills when depth is available
- partial fills
- insufficient liquidity
- simulated rejection
- entry latency
- holding period
- fees
- drawdown
- capture rate

The current normalized WebSocket feed still contains top-of-book fields rather than arbitrary L2 depth arrays. Therefore the simulator uses one executable level when bid/ask and event volume are available and explicitly records that limitation.

No live orders are sent.

## Next

The next data-collection evolution should add normalized L2 snapshots/deltas so the simulator can consume real depth and estimate:
- spread crossing
- depth consumed
- price impact
- liquidity exhaustion
- queue-aware approximations
- venue-specific execution quality.
