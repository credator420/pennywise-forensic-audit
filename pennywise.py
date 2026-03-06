import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import itertools
import numpy as np



def month_over_month(df, shock_treshold, weight_treshold):
    df['period'] = pd.to_datetime(df['date'])
    df['period'] = df['period'].dt.strftime('%Y-%m')

    result = df.groupby(['category' ,'period'])['amount'].sum()
    result = pd.DataFrame(result, columns=['amount'])
    master_calendar = []
    min_period = pd.to_datetime(min(df['period']))
    max_period = pd.to_datetime(max(df['period']))

    while(max_period >= min_period):
        dt_object = datetime.date(min_period)
        date_string = dt_object.strftime("%Y-%m")
        master_calendar.append(date_string)
        min_period += relativedelta(months=+1)
        
    unique_categories = df['category'].unique()

    arr = [unique_categories, master_calendar]

    cartesian_product = []
    for element in itertools.product(*arr):
        cartesian_product.append(element)


    cartesian_product_df = pd.DataFrame(cartesian_product, columns=['category', 'period'])

    merged_left = pd.merge(cartesian_product_df, result, on=['category', 'period'], how='left')
    merged_left = merged_left.fillna(0.00)

    merged_left['previous_amount'] = merged_left.groupby('category')['amount'].shift(1).fillna(0.00)

    merged_left['delta'] = merged_left['amount'] - merged_left['previous_amount']
    
    merged_left['pct_change'] = np.where(
        merged_left['previous_amount'] == 0,
        np.where(merged_left['amount'] == 0, 0.00, 100.0),
        (merged_left['delta']/merged_left['previous_amount']) *100
    )

    shock = merged_left['pct_change'].abs()
    weight = merged_left['delta'].abs()

    flagged = merged_left[ (shock > shock_treshold) & ((weight > weight_treshold)) ]
    
    return flagged
    
def find_duplicate(df, whitelist):
    lowered_whitelist = [str(x).lower().strip() for x in whitelist]
    
    non_whitelisted_mask = ~df['category'].str.lower().str.strip().isin(lowered_whitelist)

    audit_subset = df[non_whitelisted_mask]

    counts = audit_subset['fingerprint'].value_counts()

    return counts[counts > 1].index.tolist()

def z_score_flag(df):
    mean = df['amount'].mean()
    std_dev = df['std_dev'] = df['amount'].std()

    if std_dev == 0:
        return []
    
    df['z_score'] = (df['amount'] - mean) / std_dev
    
    flagged = df[df['z_score'].abs() > 3].index

    return flagged

def benfords_check(df):
    benford_expected = {
        '1': 30.1, '2': 17.6, '3': 12.5, '4': 9.7, 
        '5': 7.9, '6': 6.7, '7': 5.8, '8': 5.1, '9': 4.6
    }

    digits = df[df['amount'] > 0]['amount'].astype('str').str.replace('.', '').str.lstrip('0').str[0]

    counts = (digits.value_counts(normalize=True) * 100).sort_index()

    total_diff = 0
    for d, exp in benford_expected.items():
        total_diff += abs(counts.get(d, 0) - exp)
    mad = total_diff / 9

    if mad < 1.5:
        verdict = "✅ VERDICT: HIGH CONFORMITY. The data appears naturally generated."
        status_color = "success"
    elif mad < 3.5:
        verdict = "⚠️ VERDICT: MARGINAL CONFORMITY. Potential minor errors or process bias."
        status_color = "warning"
    else:
        verdict = "🚨 VERDICT: NON-CONFORMITY. High probability of manual data manipulation."
        status_color = "error"

    # 5. Look for "Splitting" (The most common fraud)
    insights = []
    one_freq = counts.get('1', 0)
    if one_freq < 25:
        insights.append("'1' frequency is low. Check for 'Invoice Splitting' to bypass limits.")
    
    five_to_nine_freq = sum([counts.get(str(i), 0) for i in range(5, 10)])
    if five_to_nine_freq > 40:
        insights.append("High frequency of 5-9. Suggests 'Budget Stuffing' or manual padding.")
 
    return {
        "mad-score": mad,
        "verdict": verdict,
        "status-color": status_color,
        "insights": insights,
        "actual-counts": counts,
        "expected-counts": benford_expected
    }

def rsf_flag(df, rsf_treshold):

    df['rank'] = df.groupby('category')['amount'].rank(method='first', ascending=False)

    top_items = df[df['rank'] <= 2].copy()

    pivot = top_items.pivot(index='category', columns='rank', values='amount')

    pivot['rsf'] = pivot[1.0] / pivot[2.0]

    high_risk_cats = pivot[pivot['rsf'] >= rsf_treshold].index

    flagged = df[(df['category'].isin(high_risk_cats)) & (df['rank'] == 1.0)].index

    return flagged  

def calculate_score(df, shock_treshold, weight_treshold, rsf_treshold, whitelist):   
    #SETUP
    df['risk_score'] = 0
    df['status'] = '✅ Low Risk'
    df['failed_tests'] = ""

    df['fingerprint'] = (
        df['category'].astype(str).str.strip() + 
        df['description'].astype(str).str.strip() +
        df['amount'].astype(str).str.strip()
    )

    lowered_whitelist = [item.lower() for item in whitelist]
    active_mask = ~df['category'].str.lower().isin(lowered_whitelist)

    flagged_mom = month_over_month(df, shock_treshold, weight_treshold)
    z_indices = z_score_flag(df)
    dup_list =find_duplicate(df, whitelist)
    rsf_indices = rsf_flag(df[active_mask], rsf_treshold)



    #MOM CHECK
    df_keys = df['category'] + "_" + pd.to_datetime(df['date']).dt.strftime("%Y-%m")
    flag_keys = flagged_mom['category'] + "_" + flagged_mom['period']

    df.loc[df_keys.isin(flag_keys), 'risk_score'] += 2
    df.loc[df_keys.isin(flag_keys), 'failed_tests'] += " [MoM Budget Shock] "


    #DUPLICATES CHECK
    df.loc[df['fingerprint'].isin(dup_list), 'risk_score'] += 5
    df.loc[df['fingerprint'].isin(dup_list), 'failed_tests'] += " [Duplicate Transaction] "

    #MEAN CHECK
    df.loc[z_indices, 'risk_score'] += 3
    df.loc[z_indices, 'failed_tests'] += " [ Z Score] "

    #RSF CHECK
    df.loc[rsf_indices, 'risk_score'] += 3
    df.loc[rsf_indices, 'failed_tests'] += " [RSF Outlier] "

    df['failed_tests'] = df['failed_tests'].str.strip().replace("", "None")

    return df

def status_labels(df):

    conditions = [
        (df['risk_score'] >= 8),
        (df['risk_score'] >= 5) & (df['risk_score'] < 8),
        (df['risk_score'] >= 2) & (df['risk_score'] < 5),
        (df['risk_score'] == 0)
    ]

    choices = [
        "🚨 CRITICAL: Immediate Investigation",
        "⚠️ HIGH RISK: Manual Audit Required",
        "🔍 MONITOR: Review Trend",
        "✅ STABLE"
    ]

    df['status'] = np.select(conditions, choices, default='UNKNOWN')

    return df

def output(df):
    calculate_score(df)
    df = status_labels(df)

    hit_list = df[df['risk_score'] > 0].sort_values(by='risk_score', ascending=False)

    total_at_risk = hit_list['amount'].sum()

    print("\n" + "="*90)
    print(f" PennyWise: EXECUTIVE AUDIT SUMMARY")
    print("="*90)
    print(f"TOTAL TRANSACTIONS SCANNED: {len(df)}")
    print(f"HIGH-RISK ANOMALIES FOUND:  {len(hit_list)}")
    print(f"TOTAL DOLLAR EXPOSURE:      ${total_at_risk:,.2f}")
    benfords_check(df)
    # 3. Print the "Top 5" with specific columns
    print("TOP 50 CRITICAL RED FLAGS:")
    # We only show the columns the boss needs to see
    cols_to_show = ['date', 'category', 'description', 'amount', 'risk_score', 'status']
    print(hit_list[cols_to_show].head(50))

    print("="*90)






