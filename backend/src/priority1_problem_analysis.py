"""
Priority 1: Problem Analysis - FIXED FOR YOUR EXCEL FORMAT
Purpose: Find all critical failures in historical data
Output: JSON report of incidents and costs
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

class ProblemAnalyzer:
    def __init__(self, excel_path='data/inventory_levels.xlsx'):
        """Load and parse the Excel data"""
        print("Loading Excel data...")
        self.df = self._load_excel_data(excel_path)
        self.critical_threshold = 500
        self.warning_threshold = 750
        
    def _load_excel_data(self, path):
        """Parse the specific format of their Excel"""
        # Read the Excel file - the headers are in row 1, not row 0
        df = pd.read_excel(path, header=1)  # Skip the "Airgas Inventory" row
        
        print(f"Columns found: {list(df.columns)}")
        
        # Clean column names
        df.columns = ['date', 'item_description', 'location', 'quantity', 'empty', 'full', 'meter_left', 'meter_right', 'extra']
        
        # Drop the extra column if it exists
        if 'extra' in df.columns:
            df = df.drop('extra', axis=1)
        
        # Convert meter readings to numeric, handling "OFF", "HALF", "FULL", etc.
        df['meter_left'] = pd.to_numeric(df['meter_left'], errors='coerce')
        df['meter_right'] = pd.to_numeric(df['meter_right'], errors='coerce')
        
        # Convert empty and full to numeric
        df['empty'] = pd.to_numeric(df['empty'], errors='coerce')
        df['full'] = pd.to_numeric(df['full'], errors='coerce')
        
        # Parse dates
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        # Remove rows with no valid date
        df = df.dropna(subset=['date'])
        
        print(f"Loaded {len(df)} rows of data")
        print(f"Date range: {df['date'].min()} to {df['date'].max()}")
        print(f"Rooms found: {df['location'].unique()}")
        
        return df
    
    def find_critical_incidents(self):
        """Find all times PSI dropped below 500"""
        incidents = []
        
        # Check each row for violations
        for idx, row in self.df.iterrows():
            # Skip if no location info
            if pd.isna(row.get('location', None)):
                continue
                
            # Check left meter
            meter_left = row.get('meter_left', None)
            if not pd.isna(meter_left) and meter_left < self.critical_threshold and meter_left > 0:
                incidents.append({
                    'date': row['date'].strftime('%Y-%m-%d'),
                    'room': row['location'],
                    'gas_type': row.get('item_description', 'Unknown'),
                    'meter': 'left',
                    'psi': float(meter_left),
                    'severity': 'CRITICAL' if meter_left < 300 else 'WARNING',
                    'estimated_cost': 1000 if meter_left < 300 else 500
                })
            
            # Check right meter
            meter_right = row.get('meter_right', None)
            if not pd.isna(meter_right) and meter_right < self.critical_threshold and meter_right > 0:
                incidents.append({
                    'date': row['date'].strftime('%Y-%m-%d'),
                    'room': row['location'],
                    'gas_type': row.get('item_description', 'Unknown'),
                    'meter': 'right',
                    'psi': float(meter_right),
                    'severity': 'CRITICAL' if meter_right < 300 else 'WARNING',
                    'estimated_cost': 1000 if meter_right < 300 else 500
                })
        
        # Sort by severity and PSI (lowest first)
        incidents = sorted(incidents, key=lambda x: (x['psi'], x['date']))
        
        return incidents
    
    def calculate_rental_waste(self):
        """Find cylinders sitting unused (Full > 0 for extended periods)"""
        waste_analysis = {}
        
        # Group by room and gas type
        grouped = self.df.groupby(['location', 'item_description'])
        
        for (room, gas), group in grouped:
            # Sort by date
            group = group.sort_values('date')
            
            # Check if "Full" cylinders sitting unused
            full_counts = group['full'].fillna(0)
            
            # Find the maximum consecutive days with full cylinders
            consecutive_days = 0
            max_consecutive = 0
            last_full_count = 0
            
            for i in range(len(full_counts)):
                current_full = full_counts.iloc[i]
                if current_full > 0:
                    if i > 0:
                        # Check if it's consecutive (next day)
                        date_diff = (group['date'].iloc[i] - group['date'].iloc[i-1]).days
                        if date_diff <= 3 and current_full == last_full_count:  # Allow weekend gaps
                            consecutive_days += date_diff
                        else:
                            consecutive_days = 1
                    else:
                        consecutive_days = 1
                    last_full_count = current_full
                    max_consecutive = max(max_consecutive, consecutive_days)
                else:
                    consecutive_days = 0
            
            # If cylinders sat for more than 7 days
            if max_consecutive > 7 and last_full_count > 0:
                waste = max_consecutive * 0.09 * last_full_count  # $0.09 per day per cylinder
                waste_analysis[f"{room}_{gas}"] = {
                    'room': room,
                    'gas': gas[:30],  # Truncate long gas names
                    'unused_cylinders': int(last_full_count),
                    'days_unused': max_consecutive,
                    'wasted_rental_cost': round(waste, 2)
                }
        
        return waste_analysis
    
    def analyze_consumption_patterns(self):
        """Analyze consumption patterns for each room"""
        patterns = {}
        
        # Group by room
        for room in self.df['location'].unique():
            room_data = self.df[self.df['location'] == room].sort_values('date')
            
            # Calculate daily consumption for each meter
            consumptions = []
            
            for i in range(1, len(room_data)):
                prev = room_data.iloc[i-1]
                curr = room_data.iloc[i]
                
                # Check left meter
                if not pd.isna(prev['meter_left']) and not pd.isna(curr['meter_left']):
                    # If PSI increased, cylinder was swapped
                    if curr['meter_left'] > prev['meter_left'] + 100:
                        consumptions.append(f"Swap at {prev['meter_left']} PSI")
                    else:
                        daily_burn = prev['meter_left'] - curr['meter_left']
                        if daily_burn > 0:
                            days_between = (curr['date'] - prev['date']).days
                            if days_between > 0:
                                consumptions.append(daily_burn / days_between)
            
            if consumptions:
                # Filter out swap messages
                numeric_consumptions = [c for c in consumptions if isinstance(c, (int, float))]
                if numeric_consumptions:
                    patterns[room] = {
                        'avg_daily_consumption': round(np.mean(numeric_consumptions), 1),
                        'max_daily_consumption': round(max(numeric_consumptions), 1),
                        'volatility': 'HIGH' if np.std(numeric_consumptions) > 50 else 'LOW'
                    }
        
        return patterns
    
    def generate_report(self):
        """Generate comprehensive problem report"""
        incidents = self.find_critical_incidents()
        waste = self.calculate_rental_waste()
        patterns = self.analyze_consumption_patterns()
        
        # Calculate totals
        total_incidents = len(incidents)
        critical_incidents = len([i for i in incidents if i['severity'] == 'CRITICAL'])
        total_incident_cost = sum(i['estimated_cost'] for i in incidents)
        total_waste_cost = sum(w['wasted_rental_cost'] for w in waste.values())
        
        report = {
            'summary': {
                'total_violations': total_incidents,
                'critical_violations': critical_incidents,
                'total_incident_cost': total_incident_cost,
                'monthly_rental_waste': round(total_waste_cost / 3, 2) if total_waste_cost else 0,
                'total_preventable_cost': total_incident_cost + total_waste_cost
            },
            'critical_incidents': incidents[:20],  # Top 20 worst incidents
            'rental_waste': list(waste.values()),
            'consumption_patterns': patterns,
            'worst_incident': incidents[0] if incidents else None
        }
        
        # Save report
        with open('outputs/problem_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        print("\n" + "="*50)
        print("PROBLEM ANALYSIS COMPLETE")
        print("="*50)
        print(f"Critical Violations Found: {critical_incidents}")
        print(f"Total Violations: {total_incidents}")
        print(f"Estimated Research Disruption Cost: ${total_incident_cost}")
        print(f"Monthly Rental Waste: ${report['summary']['monthly_rental_waste']}")
        
        if report['worst_incident']:
            print(f"\nWorst Incident: Room {report['worst_incident']['room']} at {report['worst_incident']['psi']} PSI on {report['worst_incident']['date']}")
        
        # List top 5 worst incidents
        print("\nTop 5 Critical Incidents:")
        for i, incident in enumerate(incidents[:5], 1):
            print(f"  {i}. {incident['date']}: Room {incident['room']} - {incident['psi']} PSI ({incident['gas_type'][:30]})")
        
        # Show high consumption rooms
        print("\nHigh Volatility Rooms (need adaptive ordering):")
        for room, pattern in patterns.items():
            if pattern.get('volatility') == 'HIGH':
                print(f"  {room}: {pattern['avg_daily_consumption']} PSI/day average, {pattern['max_daily_consumption']} PSI/day max")
        
        print("\nFull report saved to outputs/problem_report.json")
        
        return report

# Run if executed directly
if __name__ == "__main__":
    analyzer = ProblemAnalyzer()
    report = analyzer.generate_report()