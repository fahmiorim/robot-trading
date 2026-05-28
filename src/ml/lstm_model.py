import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
from typing import Tuple

class LSTMTradingModel(nn.Module):
    def __init__(self, input_size: int = 5, hidden_size: int = 50, num_layers: int = 2, output_size: int = 3):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, output_size)
    
    def forward(self, x):
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size)
        out, _ = self.lstm(x, (h0, c0))
        out = self.fc(out[:, -1, :])
        return out

class DeepLearningTrader:
    def __init__(self, sequence_length: int = 60):
        self.sequence_length = sequence_length
        self.scaler = MinMaxScaler()
        self.model = LSTMTradingModel()
        self.is_trained = False
    
    def prepare_sequences(self, data: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        scaled_data = self.scaler.fit_transform(data[['open', 'high', 'low', 'close', 'volume']].values)
        X, y = [], []
        for i in range(self.sequence_length, len(scaled_data)):
            X.append(scaled_data[i-self.sequence_length:i])
            price_change = scaled_data[i, 3] - scaled_data[i-1, 3]
            if price_change > 0.001:
                y.append(1)
            elif price_change < -0.001:
                y.append(-1)
            else:
                y.append(0)
        return np.array(X), np.array(y)
    
    def train(self, data: pd.DataFrame, epochs: int = 50, batch_size: int = 32) -> float:
        X, y = self.prepare_sequences(data)
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        train_dataset = TensorDataset(torch.FloatTensor(X_train), torch.LongTensor(y_train))
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        criterion = nn.CrossEntropyLoss()
        optimizer = torch.optim.Adam(self.model.parameters(), lr=0.001)
        for epoch in range(epochs):
            for X_batch, y_batch in train_loader:
                optimizer.zero_grad()
                outputs = self.model(X_batch)
                loss = criterion(outputs, y_batch)
                loss.backward()
                optimizer.step()
        self.model.eval()
        with torch.no_grad():
            test_outputs = self.model(torch.FloatTensor(X_test))
            predictions = torch.argmax(test_outputs, dim=1).numpy()
            accuracy = (predictions == y_test).mean()
        self.is_trained = True
        return accuracy
    
    def predict(self, data: pd.DataFrame) -> np.ndarray:
        if not self.is_trained:
            raise ValueError("Model must be trained first")
        scaled_data = self.scaler.transform(data[['open', 'high', 'low', 'close', 'volume']].values)
        X = []
        for i in range(self.sequence_length, len(scaled_data)):
            X.append(scaled_data[i-self.sequence_length:i])
        X = torch.FloatTensor(np.array(X))
        self.model.eval()
        with torch.no_grad():
            outputs = self.model(X)
            predictions = torch.argmax(outputs, dim=1).numpy()
        return predictions
