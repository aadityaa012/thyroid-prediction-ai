
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier

# Load dataset
data = pd.read_csv("thyroid.csv")

# Select input features
X = data[["age", "tsh", "t3", "t4"]]

# Select output labels
y = data["label"]

# Create and train model
model = RandomForestClassifier(random_state=42)
model.fit(X, y)

# Save trained model
joblib.dump(model, "model.pkl")

print("Thyroid prediction model trained successfully!")
