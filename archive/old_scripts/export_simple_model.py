import torch
import torch.nn as nn
import json

# ---------------------------------------------------------
# SIMPLIFIED MODEL FOR EZKL COMPATIBILITY
# ---------------------------------------------------------
class SimpleCarbonValidator(nn.Module):
    """
    Ultra-simple model: just Linear + ReLU layers
    (ezkl has issues with Sigmoid/BCEWithLogitsLoss)
    """
    def __init__(self, input_dim=6):
        super(SimpleCarbonValidator, self).__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1)  # Output logit
        )

    def forward(self, x):
        return self.network(x)


def export_simple_model():
    """
    Export a simple ONNX model compatible with ezkl
    """
    print("Creating simplified model for ezkl compatibility...")
    
    model = SimpleCarbonValidator(input_dim=6)
    
    # Create dummy input
    dummy_input = torch.randn(1, 6, dtype=torch.float32)
    
    # Export to ONNX
    print("Exporting to ONNX...")
    torch.onnx.export(
        model,
        dummy_input,
        "carbon_validator_simple.onnx",
        export_params=True,
        opset_version=11,
        do_constant_folding=True,
        input_names=['input'],
        output_names=['output'],
        verbose=False
    )
    
    print("✓ Exported: carbon_validator_simple.onnx")
    
    # Create dummy input.json for testing
    sample_input = [[424.8, 51.2, 22.1, 44.6, 34.0562, -118.2336]]
    with open("input.json", "w") as f:
        json.dump(sample_input, f)
    print("✓ Created: input.json")
    
    return "carbon_validator_simple.onnx"


if __name__ == "__main__":
    export_simple_model()
