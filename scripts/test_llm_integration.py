import sys
from pathlib import Path

# Add src to python path to load predi_care
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from predi_care.engine.mock_factory import PRESET_SCENARIOS
from predi_care.engine.llm_client import call_medical_llm

def test_integration():
    print("Testing NVIDIA NIM LLM Integration...")
    
    # Test with predefined profile A: Indication chirurgicale claire
    patient_data = PRESET_SCENARIOS["Indication chirurgicale claire"]
    
    # Needs to be wrapped in the structured dict
    from predi_care.engine.brain_engine_v2 import _build_patient_context
    context = _build_patient_context(patient_data)
    
    print("\nCalling LLM API... (ensure NVIDIA_API_KEY is in .streamlit/secrets.toml or ENV)")
    response = call_medical_llm(context)
    
    if response:
        print("\n✅ SUCCESS: LLM returned structured response!")
        print(f"Recommendation: {response.recommendation}")
        print(f"Surgical DFS 5y: {response.surgery.survival_dfs_5y}%")
        print(f"W&W Preservation 2y: {response.watch_wait.organ_preservation_2y}%")
        print("\nKey Factors:")
        for kf in response.key_factors[:3]:
            print(f"- {kf.factor}: {kf.direction} (impact: {kf.impact_magnitude})")
    else:
        print("\n❌ FAILED: LLM returned None. Falling back to heuristic engine.")

if __name__ == "__main__":
    test_integration()
