"""
Priority 3: Order Optimization Engine
Purpose: Generate specific orders and reallocation suggestions
Output: Actionable order list for Monday morning
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

class OrderOptimizer:
    def __init__(self):
        """Initialize with forecast data"""
        print("Loading forecast data...")
        with open('outputs/weekly_forecast.json', 'r') as f:
            self.forecast = json.load(f)
        
        # Load current inventory
        self.inventory = self._load_current_inventory()
        
        # Costs
        self.rental_cost_per_day = 0.09
        self.stockout_cost = 1000
        self.order_lead_time = 2  # days
        
    def _load_current_inventory(self):
        """Load current inventory state"""
        df = pd.read_excel('data/inventory_levels.xlsx', header=1)
        df.columns = ['date', 'item_description', 'location', 'quantity', 'empty', 'full', 'meter_left', 'meter_right', 'extra']
        
        # Get latest state for each room
        latest = df.groupby('location').last()
        
        inventory = {}
        for room in latest.index:
            inventory[room] = {
                'full_cylinders': int(latest.loc[room, 'full']) if not pd.isna(latest.loc[room, 'full']) else 0,
                'empty_cylinders': int(latest.loc[room, 'empty']) if not pd.isna(latest.loc[room, 'empty']) else 0,
                'gas_type': latest.loc[room, 'item_description'],
                'total_capacity': int(latest.loc[room, 'quantity']) if not pd.isna(latest.loc[room, 'quantity']) else 4
            }
        
        return inventory
    
    def generate_orders(self):
        """Generate optimal orders for the week"""
        orders = []
        
        for room, data in self.forecast['room_forecasts'].items():
            if 'error' in data:
                continue
                
            # Determine order quantity based on urgency
            if data['recommendation'] == 'SWAP_IMMEDIATELY':
                # Use existing inventory first
                if self.inventory[room]['full_cylinders'] > 0:
                    orders.append({
                        'action': 'SWAP',
                        'room': room,
                        'gas_type': self.inventory[room]['gas_type'],
                        'urgency': 'IMMEDIATE',
                        'reason': f"Currently at {data['current_psi']} PSI - Use spare cylinder"
                    })
                else:
                    orders.append({
                        'action': 'ORDER',
                        'room': room,
                        'gas_type': self.inventory[room]['gas_type'],
                        'quantity': 2,
                        'urgency': 'EMERGENCY',
                        'reason': f"CRITICAL: {data['current_psi']} PSI, no spares available"
                    })
                    
            elif data['recommendation'] in ['ORDER_TODAY_URGENT', 'ORDER_THIS_WEEK']:
                # Calculate optimal order quantity
                volatility = data.get('volatility', 'MEDIUM')
                
                if volatility == 'HIGH':
                    quantity = 2  # Order extra for volatile rooms
                else:
                    quantity = 1
                
                # Check if we can wait for batch ordering
                if data['days_until_critical'] > 3:
                    order_day = 'Thursday'  # Batch orders
                    urgency = 'NORMAL'
                else:
                    order_day = 'Monday'
                    urgency = 'HIGH'
                
                orders.append({
                    'action': 'ORDER',
                    'room': room,
                    'gas_type': self.inventory[room]['gas_type'],
                    'quantity': quantity,
                    'order_day': order_day,
                    'urgency': urgency,
                    'reason': f"{data['days_until_critical']:.1f} days until critical, burning {data['avg_daily_burn']:.0f} PSI/day"
                })
        
        return orders
    
    def identify_reallocations(self):
        """Find opportunities to move cylinders between rooms"""
        reallocations = []
        
        # Find rooms with excess inventory
        donors = []
        recipients = []
        
        for room, inv in self.inventory.items():
            forecast = self.forecast['room_forecasts'].get(room, {})
            
            # Rooms with full cylinders and low consumption
            if inv['full_cylinders'] > 1 and forecast.get('regime') == 'OFF':
                donors.append({
                    'room': room,
                    'available': inv['full_cylinders'] - 1,  # Keep 1 for safety
                    'gas_type': inv['gas_type']
                })
            
            # Rooms needing cylinders urgently
            if inv['full_cylinders'] == 0 and forecast.get('days_until_critical', 999) < 5:
                recipients.append({
                    'room': room,
                    'gas_type': inv['gas_type'],
                    'urgency': forecast.get('days_until_critical', 999)
                })
        
        # Match donors with recipients (same gas type)
        for recipient in sorted(recipients, key=lambda x: x['urgency']):
            for donor in donors:
                if donor['gas_type'] == recipient['gas_type'] and donor['available'] > 0:
                    reallocations.append({
                        'from': donor['room'],
                        'to': recipient['room'],
                        'gas_type': donor['gas_type'],
                        'urgency': 'HIGH' if recipient['urgency'] < 2 else 'MEDIUM',
                        'reason': f"Donor has {donor['available']} spare, recipient at {recipient['urgency']:.1f} days to critical"
                    })
                    donor['available'] -= 1
                    break
        
        return reallocations
    
    def calculate_savings(self, orders, reallocations):
        """Calculate cost savings from optimization"""
        # Prevented stockouts
        prevented_stockouts = len([o for o in orders if o.get('urgency') in ['IMMEDIATE', 'EMERGENCY']])
        stockout_savings = prevented_stockouts * self.stockout_cost
        
        # Rental savings from reallocations (avoid ordering new)
        rental_savings = len(reallocations) * 14 * self.rental_cost_per_day  # 2 weeks rental avoided
        
        # Batch ordering savings (assumed 10% discount)
        batch_orders = len([o for o in orders if o.get('order_day') == 'Thursday'])
        batch_savings = batch_orders * 50 * 0.1  # Assume $50 per cylinder, 10% discount
        
        return {
            'prevented_stockouts': prevented_stockouts,
            'stockout_savings': stockout_savings,
            'rental_savings': round(rental_savings, 2),
            'batch_savings': round(batch_savings, 2),
            'total_weekly_savings': round(stockout_savings + rental_savings + batch_savings, 2)
        }
    
    def generate_action_plan(self):
        """Generate complete action plan for the week"""
        print("\n" + "="*50)
        print("OPTIMIZATION COMPLETE - MONDAY ACTION PLAN")
        print("="*50)
        
        orders = self.generate_orders()
        reallocations = self.identify_reallocations()
        savings = self.calculate_savings(orders, reallocations)
        
        # Sort by urgency
        immediate_actions = [o for o in orders if o.get('urgency') in ['IMMEDIATE', 'EMERGENCY', 'HIGH']]
        routine_orders = [o for o in orders if o.get('urgency') == 'NORMAL']
        
        # Print immediate actions
        print("\n🚨 IMMEDIATE ACTIONS (Monday Morning):")
        for action in immediate_actions:
            if action['action'] == 'SWAP':
                print(f"  - SWAP cylinder in {action['room']} NOW - {action['reason']}")
            else:
                print(f"  - ORDER {action['quantity']} {action['gas_type'][:20]} for {action['room']} - {action['reason']}")
        
        # Print reallocations
        if reallocations:
            print("\n🔄 REALLOCATION OPPORTUNITIES:")
            for realloc in reallocations:
                print(f"  - Move 1 {realloc['gas_type'][:20]} from {realloc['from']} to {realloc['to']}")
        
        # Print routine orders
        if routine_orders:
            print("\n📋 ROUTINE ORDERS (Can batch Thursday):")
            for order in routine_orders:
                print(f"  - Order {order['quantity']} {order['gas_type'][:20]} for {order['room']} - {order['reason']}")
        
        # Print savings
        print("\n💰 WEEKLY SAVINGS:")
        print(f"  - Prevented Stockouts: {savings['prevented_stockouts']} (${savings['stockout_savings']})")
        print(f"  - Rental Optimization: ${savings['rental_savings']}")
        print(f"  - Batch Order Discount: ${savings['batch_savings']}")
        print(f"  - TOTAL SAVINGS: ${savings['total_weekly_savings']}")
        
        # Save action plan
        action_plan = {
            'generated_at': datetime.now().isoformat(),
            'immediate_actions': immediate_actions,
            'reallocations': reallocations,
            'routine_orders': routine_orders,
            'savings': savings,
            'monday_checklist': [
                f"✓ {a['action']} - {a['room']}" for a in immediate_actions
            ]
        }
        
        with open('outputs/monday_action_plan.json', 'w') as f:
            json.dump(action_plan, f, indent=2)
        
        print("\nAction plan saved to outputs/monday_action_plan.json")
        
        return action_plan

# Run if executed directly
if __name__ == "__main__":
    optimizer = OrderOptimizer()
    action_plan = optimizer.generate_action_plan()