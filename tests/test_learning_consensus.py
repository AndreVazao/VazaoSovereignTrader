from PC_ENGINE.learning.learning_consensus import PaperLearningConsensus


def test_consensus_requires_both_sources(tmp_path):
    learning = tmp_path / "learning.jsonl"
    outcomes = tmp_path / "outcomes.jsonl"
    learning.write_text(
        '{"signature":"BULL|UP|LOW|BUY|cp|q|","horizon_ms":5000,"samples":40,"wins":30,"win_rate":0.75,"mean_net_bps":5,"median_net_bps":4,"lower_ci_bps":2,"eligible":true}\n',
        encoding="utf-8",
    )
    outcomes.write_text(
        '{"symbol":"BTC/USDT","action":"BUY","regime":"BULL","horizon_ms":5000,"samples":40,"wins":30,"win_rate":0.75,"mean_net_bps":5,"median_net_bps":4,"lower_ci_bps":2,"eligible":true}\n',
        encoding="utf-8",
    )
    # The exact signature hierarchy is tested by the learner; this test only
    # verifies that an unrelated state does not receive a bonus.
    state = {"symbol":"ETH/USDT","action":"BUY","regime":"BULL","trend":"UP","volatility":"LOW"}
    result = PaperLearningConsensus({"learning_path":str(learning),"outcome_path":str(outcomes)}).evaluate(state)
    assert result.bonus == 0.0
    assert not result.agreement
