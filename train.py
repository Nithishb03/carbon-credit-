import torch
import torch.nn as nn
import torch.optim as optim
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix

# ---------------------------------------------------------
# 1. THE NEURAL NETWORK ARCHITECTURE
# ---------------------------------------------------------
class CarbonValidatorMLP(nn.Module):
    def __init__(self, input_dim):
        super(CarbonValidatorMLP, self).__init__()
        # We keep the network relatively shallow to ensure low Gas/Compute costs 
        # when converting to a ZK-SNARK circuit later.
        self.network = nn.Sequential(
            nn.Linear(input_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 1) # Raw logit output (No Sigmoid here, handled by Loss function)
        )

    def forward(self, x):
        return self.network(x)

# ---------------------------------------------------------
# 2. DATA LOADING & PREPROCESSING
# ---------------------------------------------------------
def train_validator_model(dataset_path="carbon_100k_ctgan.csv", onnx_output="carbon_validator.onnx"):
    print(f"Loading 100k Dataset from {dataset_path}...")
    df = pd.read_csv(dataset_path)

    # Define Features and Target
    features = ['power_kwh', 'vibration_hz', 'temp_c', 'humidity_pct', 'gps_lat', 'gps_long']
    X = df[features].values
    y = df['label'].values

    # Train/Test Split (80% Train, 20% Test)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    # Scaling is CRITICAL for Neural Networks
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Convert to PyTorch Tensors
    X_train_tensor = torch.tensor(X_train_scaled, dtype=torch.float32)
    y_train_tensor = torch.tensor(y_train, dtype=torch.float32).view(-1, 1)
    X_test_tensor = torch.tensor(X_test_scaled, dtype=torch.float32)
    y_test_tensor = torch.tensor(y_test, dtype=torch.float32).view(-1, 1)

    # ---------------------------------------------------------
    # 3. TRAINING SETUP (Handling Class Imbalance)
    # ---------------------------------------------------------
    # Calculate positive weight to penalize the model for missing anomalies
    num_neg = (y_train == 0).sum()
    num_pos = (y_train == 1).sum()
    pos_weight = torch.tensor([num_neg / num_pos], dtype=torch.float32)
    
    print(f"Calculated Positive Weight for Imbalance: {pos_weight.item():.2f}")

    model = CarbonValidatorMLP(input_dim=len(features))
    
    # BCEWithLogitsLoss applies Sigmoid internally (better numerical stability)
    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    # ---------------------------------------------------------
    # 4. TRAINING LOOP
    # ---------------------------------------------------------
    epochs = 200
    batch_size = 256
    dataset = torch.utils.data.TensorDataset(X_train_tensor, y_train_tensor)
    dataloader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=True)

    print("\nStarting Training...")
    for epoch in range(epochs):
        model.train()
        epoch_loss = 0
        for batch_X, batch_y in dataloader:
            optimizer.zero_grad()
            predictions = model(batch_X)
            loss = criterion(predictions, batch_y)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()
            
        if (epoch + 1) % 50 == 0:
            print(f"Epoch {epoch+1}/{epochs} | Loss: {epoch_loss/len(dataloader):.4f}")

    # ---------------------------------------------------------
    # 5. MODEL EVALUATION (The Proof)
    # ---------------------------------------------------------
    model.eval()
    with torch.no_grad():
        test_predictions = model(X_test_tensor)
        # Apply sigmoid to get probabilities, then threshold at 0.5
        probabilities = torch.sigmoid(test_predictions)
        predicted_classes = (probabilities >= 0.5).float().numpy()

    print("\n--- MODEL PROOF: EVALUATION REPORT ---")
    print(classification_report(y_test, predicted_classes, target_names=["Normal (0)", "Anomaly (1)"]))
    
    print("--- CONFUSION MATRIX ---")
    cm = confusion_matrix(y_test, predicted_classes)
    print(f"True Negatives (Normal OK): {cm[0][0]}")
    print(f"False Positives (False Alarm): {cm[0][1]}")
    print(f"False Negatives (Missed Fraud): {cm[1][0]}")
    print(f"True Positives (Caught Fraud): {cm[1][1]}")

    # ---------------------------------------------------------
    # 6. EXPORT TO ONNX (For ZK-ML / Blockchain)
    # ---------------------------------------------------------
    print("\nExporting Model to ONNX format for EZKL...")
    model.eval()  # Ensure model is in eval mode
    dummy_input = torch.randn(1, len(features), dtype=torch.float32)
    
    # Disable verbose ONNX export to avoid encoding issues
    import os
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    
    try:
        torch.onnx.export(
            model, 
            dummy_input, 
            onnx_output, 
            export_params=True, 
            opset_version=17,
            do_constant_folding=True, 
            input_names=['input'], 
            output_names=['output'],
            verbose=False
        )
    except Exception as e:
        print(f"ONNX export error (attempting workaround): {e}")
        # Fallback: try with even simpler export
        torch.onnx.export(
            model, 
            dummy_input, 
            onnx_output, 
            export_params=True,
            input_names=['input'],
            output_names=['output']
        )
    
    print(f"Successfully saved ONNX model to {onnx_output}")
    
    # Save the scaler mean/variance so you can scale real IoT data later!
    np.save("scaler_mean.npy", scaler.mean_)
    np.save("scaler_scale.npy", scaler.scale_)
    print("Saved StandardScaler parameters.")

if __name__ == "__main__":
    train_validator_model()