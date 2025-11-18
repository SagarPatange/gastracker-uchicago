"""
Priority 2: Adaptive Consumption Predictor
Purpose: Handle volatile consumption from experiments
Output: 7-day forecast with confidence bands
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import warnings
warnings.filterwarnings('ignore')

class AdaptivePredictor:
    def __init__(self, excel_path='data/inventory_levels.xlsx'):
        """Load data and identify consumption patterns"""
        print("Initializing Adaptive Predictor...")
        self.df = self._load_data(excel_path)
        self.consumption_history = self._calculate_consumption_rates()
        
    def _load_data(self, path):
        """Load the Excel data"""
        df = pd.read_excel(path, header=1)
        df.columns = ['date', 'item_description', 'location', 'quantity', 'empty', 'full', 'meter_left', 'meter_right', 'extra']
        df = df.drop('extra', axis=1)
        
        # Convert to numeric
        df['meter_left'] = pd.to_numeric(df['meter_left'], errors='coerce')
        df['meter_right'] = pd.to_numeric(df['meter_right'], errors='coerce')
        df['date'] = pd.to_datetime(df['date'])
        
        return df.dropna(subset=['date'])
    
    def _calculate_consumption_rates(self):
        """Calculate actual daily consumption, filtering out cylinder swaps"""
        consumption = {}
        
        for room in self.df['location'].unique():
            room_data = self.df[self.df['location'] == room].sort_values('date')
            
            daily_rates = []
            swap_events = []
            
            for i in range(1, len(room_data)):
                prev = room_data.iloc[i-1]
                curr = room_data.iloc[i]
                days_between = (curr['date'] - prev['date']).days
                
                if days_between == 0:
                    continue
                
                # Check left meter
                if not pd.isna(prev['meter_left']) and not pd.isna(curr['meter_left']):
                    if curr['meter_left'] > prev['meter_left'] + 500:
                        # This is a cylinder swap
                        swap_events.append({
                            'date': curr['date'],
                            'final_psi': prev['meter_left'],
                            'new_psi': curr['meter_left']
                        })
                    else:
                        # Normal consumption
                        daily_burn = (prev['meter_left'] - curr['meter_left']) / days_between
                        if 0 < daily_burn < 500:  # Filter out anomalies
                            daily_rates.append(daily_burn)
                
                # Check right meter
                if not pd.isna(prev['meter_right']) and not pd.isna(curr['meter_right']):
                    if curr['meter_right'] > prev['meter_right'] + 500:
                        swap_events.append({
                            'date': curr['date'],
                            'final_psi': prev['meter_right'],
                            'new_psi': curr['meter_right']
                        })
                    else:
                        daily_burn = (prev['meter_right'] - curr['meter_right']) / days_between
                        if 0 < daily_burn < 500:
                            daily_rates.append(daily_burn)
            
            consumption[room] = {
                'daily_rates': daily_rates,
                'swap_events': swap_events,
                'avg_consumption': np.mean(daily_rates) if daily_rates else 0,
                'std_consumption': np.std(daily_rates) if daily_rates else 0,
                'max_consumption': max(daily_rates) if daily_rates else 0
            }
        
        return consumption
    
    def detect_regime(self, room, recent_days=7):
        """Detect if room is in normal, high-experiment, or off mode"""
        room_data = self.df[self.df['location'] == room].tail(recent_days)
        
        if len(room_data) < 2:
            return 'UNKNOWN'
        
        # Calculate recent consumption
        recent_consumption = []
        for i in range(1, len(room_data)):
            prev = room_data.iloc[i-1]
            curr = room_data.iloc[i]
            
            for meter in ['meter_left', 'meter_right']:
                if not pd.isna(prev[meter]) and not pd.isna(curr[meter]):
                    if 0 < curr[meter] < prev[meter]:  # Valid consumption
                        daily = prev[meter] - curr[meter]
                        recent_consumption.append(daily)
        
        if not recent_consumption:
            return 'OFF'
        
        avg_recent = np.mean(recent_consumption)
        historical_avg = self.consumption_history[room]['avg_consumption']
        
        if avg_recent < historical_avg * 0.2:
            return 'OFF'
        elif avg_recent > historical_avg * 1.5:
            return 'HIGH_EXPERIMENT'
        else:
            return 'NORMAL'
    
    def predict_with_uncertainty(self, room, days_ahead=7):
        """Predict consumption with confidence bands"""
        history = self.consumption_history.get(room, {})
        
        if not history['daily_rates']:
            return {
                'room': room,
                'error': 'No historical data',
                'recommendation': 'ORDER_IMMEDIATELY'
            }
        
        # Detect current regime
        regime = self.detect_regime(room)
        
        # Get room's current PSI
        latest = self.df[self.df['location'] == room].iloc[-1]
        current_left = latest.get('meter_left', 0)
        current_right = latest.get('meter_right', 0)
        current_psi = max(current_left, current_right) if not pd.isna(current_left) else 0
        
        # Base prediction on regime
        if regime == 'OFF':
            daily_prediction = 0
            uncertainty = 10
        elif regime == 'HIGH_EXPERIMENT':
            # Use maximum observed rate for safety
            daily_prediction = history['max_consumption']
            uncertainty = history['std_consumption']
        else:  # NORMAL
            daily_prediction = history['avg_consumption']
            uncertainty = history['std_consumption']
        
        # Generate daily forecasts
        forecast = []
        cumulative_consumption = 0
        
        for day in range(1, days_ahead + 1):
            cumulative_consumption += daily_prediction
            
            # Add weekend factor (lower consumption)
            current_date = datetime.now() + timedelta(days=day)
            if current_date.weekday() >= 5:  # Weekend
                day_consumption = daily_prediction * 0.5
            else:
                day_consumption = daily_prediction
            
            predicted_psi = current_psi - cumulative_consumption
            
            # Calculate when we hit critical levels
            days_until_500 = (current_psi - 500) / daily_prediction if daily_prediction > 0 else 999
            days_until_empty = current_psi / daily_prediction if daily_prediction > 0 else 999
            
            forecast.append({
                'day': day,
                'date': current_date.strftime('%Y-%m-%d'),
                'expected_consumption': round(day_consumption, 1),
                'worst_case_consumption': round(day_consumption + 2*uncertainty, 1),
                'predicted_psi': round(predicted_psi, 1),
                'confidence': 'HIGH' if uncertainty < 50 else 'LOW'
            })
        
        return {
            'room': room,
            'regime': regime,
            'current_psi': round(current_psi, 1),
            'avg_daily_burn': round(daily_prediction, 1),
            'volatility': 'HIGH' if uncertainty > 100 else 'MEDIUM' if uncertainty > 50 else 'LOW',
            'days_until_critical': round(days_until_500, 1),
            'days_until_empty': round(days_until_empty, 1),
            'forecast': forecast,
            'recommendation': self._generate_recommendation(current_psi, days_until_500, regime)
        }
    
    def _generate_recommendation(self, current_psi, days_until_critical, regime):
        """Generate ordering recommendation"""
        if current_psi < 500:
            return 'SWAP_IMMEDIATELY'
        elif days_until_critical < 2:
            return 'ORDER_TODAY_URGENT'
        elif days_until_critical < 5:
            return 'ORDER_THIS_WEEK'
        elif regime == 'HIGH_EXPERIMENT':
            return 'MONITOR_CLOSELY'
        else:
            return 'OK_FOR_NOW'
    
    def generate_weekly_forecast(self):
        """Generate forecasts for all rooms"""
        print("\n" + "="*50)
        print("ADAPTIVE FORECAST GENERATION")
        print("="*50)
        
        forecasts = {}
        critical_rooms = []
        order_schedule = []
        
        # Focus on high-risk rooms from our analysis
        priority_rooms = ['Room 292', 'Room 306', 'Room 278', 'Room 392']
        
        for room in priority_rooms:
            print(f"\nAnalyzing {room}...")
            forecast = self.predict_with_uncertainty(room)
            forecasts[room] = forecast
            
            # Check if critical
            if forecast.get('recommendation') in ['SWAP_IMMEDIATELY', 'ORDER_TODAY_URGENT']:
                critical_rooms.append(room)
                order_schedule.append({
                    'room': room,
                    'urgency': 'CRITICAL',
                    'current_psi': forecast.get('current_psi'),
                    'days_remaining': forecast.get('days_until_critical')
                })
            elif forecast.get('recommendation') == 'ORDER_THIS_WEEK':
                order_schedule.append({
                    'room': room,
                    'urgency': 'NORMAL',
                    'current_psi': forecast.get('current_psi'),
                    'days_remaining': forecast.get('days_until_critical')
                })
            
            # Print summary
            print(f"  Current PSI: {forecast.get('current_psi')}")
            print(f"  Regime: {forecast.get('regime')}")
            print(f"  Daily Burn: {forecast.get('avg_daily_burn')} PSI/day")
            print(f"  Days Until Critical: {forecast.get('days_until_critical')}")
            print(f"  Recommendation: {forecast.get('recommendation')}")
        
        # Save forecast
        report = {
            'generated_at': datetime.now().isoformat(),
            'critical_rooms': critical_rooms,
            'order_schedule': order_schedule,
            'room_forecasts': forecasts
        }
        
        with open('outputs/weekly_forecast.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print("\n" + "="*50)
        print(f"CRITICAL ROOMS NEEDING IMMEDIATE ATTENTION: {len(critical_rooms)}")
        for room in critical_rooms:
            print(f"  🚨 {room}")
        
        print(f"\nTotal Orders Needed This Week: {len(order_schedule)}")
        print("Forecast saved to outputs/weekly_forecast.json")
        
        return report

# Run if executed directly
if __name__ == "__main__":
    predictor = AdaptivePredictor()
    forecast = predictor.generate_weekly_forecast()