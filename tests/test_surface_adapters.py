from PC_ENGINE.execution.surface_adapters import ActionKind, Surface, SurfaceAction, SurfaceFeedback, feedback_record, paper_action

def test_adapter_action_is_forced_to_paper():
    action = paper_action(SurfaceAction('req-1','venue',Surface.ANDROID_APK,ActionKind.BUY,False))
    assert action.paper_only is True

def test_feedback_contains_transport_evidence_not_authorization():
    record = feedback_record(SurfaceFeedback('req-1',Surface.WEB_BROWSER,'venue','READY',True,123))
    assert record['acknowledged'] is True
    assert record['paper_only'] is True
    assert record['execution_authorized'] is False