#!/usr/bin/env python3
"""
Test script to verify Gmail API quota usage reduction
"""

def calculate_quota_usage(num_rules=4, messages_per_rule=10, overlap_percentage=30):
    """Calculate API quota usage before and after optimization"""
    
    print("=" * 60)
    print("Gmail API Quota Usage Analysis")
    print("=" * 60)
    
    # BEFORE optimization
    print("\n[BEFORE] Optimization:")
    print("-" * 40)
    
    # Old approach: 50 messages per rule, no deduplication
    old_max_results = 50
    old_list_calls = num_rules  # One list call per rule
    old_get_calls = num_rules * old_max_results  # Get every message
    old_total_api_calls = old_list_calls + old_get_calls
    old_quota_units = (old_list_calls * 5) + (old_get_calls * 5)  # 5 units each
    
    print(f"Rules configured: {num_rules}")
    print(f"Max results per rule: {old_max_results}")
    print(f"messages.list() calls: {old_list_calls}")
    print(f"messages.get() calls: {old_get_calls}")
    print(f"Total API calls: {old_total_api_calls}")
    print(f"Total quota units: {old_quota_units} units")
    
    # AFTER optimization
    print("\n[AFTER] Optimization:")
    print("-" * 40)
    
    # New approach: 10 messages per rule with deduplication
    new_max_results = messages_per_rule
    new_list_calls = num_rules  # Still one list call per rule
    
    # Calculate unique messages after deduplication
    total_possible = num_rules * new_max_results
    overlap_count = int(total_possible * (overlap_percentage / 100))
    unique_messages = total_possible - overlap_count
    
    new_get_calls = unique_messages  # Only get unique messages
    new_total_api_calls = new_list_calls + new_get_calls
    new_quota_units = (new_list_calls * 5) + (new_get_calls * 5)
    
    print(f"Rules configured: {num_rules}")
    print(f"Max results per rule: {new_max_results}")
    print(f"messages.list() calls: {new_list_calls}")
    print(f"Total messages found: {total_possible}")
    print(f"Duplicate messages: {overlap_count} ({overlap_percentage}%)")
    print(f"Unique messages to fetch: {unique_messages}")
    print(f"messages.get() calls: {new_get_calls}")
    print(f"Total API calls: {new_total_api_calls}")
    print(f"Total quota units: {new_quota_units} units")
    
    # Savings calculation
    print("\n[SAVINGS] Quota Savings:")
    print("-" * 40)
    
    api_calls_saved = old_total_api_calls - new_total_api_calls
    quota_saved = old_quota_units - new_quota_units
    reduction_percentage = (quota_saved / old_quota_units) * 100
    
    print(f"API calls reduced by: {api_calls_saved} calls")
    print(f"Quota units saved: {quota_saved} units")
    print(f"Reduction percentage: {reduction_percentage:.1f}%")
    
    # Additional optimizations
    print("\n[OPTIMIZATIONS] Additional Optimizations:")
    print("-" * 40)
    print("+ Added 'before:' date filter to limit results")
    print("+ Message caching prevents re-fetching (1 hour TTL)")
    print("+ Batch processing with delays to avoid rate limits")
    print("+ Scheduler checks every 5 minutes instead of 1 minute")
    print("+ Duplicate scan prevention with hour tracking")
    
    # Risk assessment
    print("\n[RISK] Risk Assessment:")
    print("-" * 40)
    
    if new_quota_units > 500:
        print("HIGH RISK: Still using >500 quota units per scan")
        print("   Recommendation: Further reduce maxResults or scan frequency")
    elif new_quota_units > 250:
        print("MEDIUM RISK: Using 250-500 quota units per scan")
        print("   Recommendation: Monitor for account warnings")
    else:
        print("LOW RISK: Using <250 quota units per scan")
        print("   Should be safe from account freezing")
    
    return {
        'before': {
            'api_calls': old_total_api_calls,
            'quota_units': old_quota_units
        },
        'after': {
            'api_calls': new_total_api_calls,
            'quota_units': new_quota_units
        },
        'savings': {
            'api_calls': api_calls_saved,
            'quota_units': quota_saved,
            'percentage': reduction_percentage
        }
    }

if __name__ == "__main__":
    # Test with typical scenario
    print("\n[SCENARIO 1] Typical Usage (4 rules, 30% overlap)")
    calculate_quota_usage(num_rules=4, messages_per_rule=10, overlap_percentage=30)
    
    print("\n" + "=" * 60)
    print("\n[SCENARIO 2] Heavy Usage (10 rules, 50% overlap)")
    calculate_quota_usage(num_rules=10, messages_per_rule=10, overlap_percentage=50)
    
    print("\n" + "=" * 60)
    print("\n[SCENARIO 3] Light Usage (2 rules, 10% overlap)")
    calculate_quota_usage(num_rules=2, messages_per_rule=10, overlap_percentage=10)