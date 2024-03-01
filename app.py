import nextcloud_client
import os
import pandas as pd
import piecash
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dotenv import load_dotenv
load_dotenv()

token = os.environ.get('INTERLAB_TOKEN')
storage_options = {'Authorization': 'Token ' + token}

url = os.environ.get('INTERLAB_URL') + 'opening/'
df_opening = pd.read_json(url, storage_options=storage_options)

url = os.environ.get('INTERLAB_URL') + 'machine_slot/'
df_machine_slot = pd.read_json(url, storage_options=storage_options, convert_dates=['start', 'end'])

url = os.environ.get('INTERLAB_URL') + 'opening_slot/'
df_opening_slot = pd.read_json(url, storage_options=storage_options, convert_dates=['start', 'end'])

url = os.environ.get('INTERLAB_URL') + 'custom_user/'
df_custom_user = pd.read_json(url, storage_options=storage_options, convert_dates=['start', 'end'])

url = os.environ.get('INTERLAB_URL') + 'subscription/'
df_subscription = pd.read_json(url, storage_options=storage_options, convert_dates=['start', 'end'])

nc_user = os.environ.get('NEXTCLOUD_USER')
nc_password = os.environ.get('NEXTCLOUD_PASSWORD')
nc = nextcloud_client.Client(os.environ.get('NEXTCLOUD_URL'))
nc.login(nc_user, nc_password)

@st.cache_data
def load_gnucash_book(file):
    nc.get_file(file, 'fablab.gnucash')

load_gnucash_book(os.environ.get('NEXTCLOUD_FILE'))

book = piecash.open_book('fablab.gnucash')    

# Plot openings as function of the superusers
st.title("Temps d'ouverture par mois groupé par super-utilisateurs.rices ou type d'ouverture")

option = {
    'Superuser': 'first_name', 
    'Ouverture': 'title'
}

key = st.selectbox('Group by', (i for i in option))

df = df_opening_slot.merge(df_custom_user, how='inner', left_on='user', right_on='id')
df = df.merge(df_opening, how='inner', left_on='opening_id', right_on='id')
df['month'] = pd.to_datetime(df['start']).dt.strftime('%y-%m')
df = df.groupby(['month', 'user', 'first_name', 'title'])['duration'].sum().reset_index()

monthly_totals = df.groupby('month')['duration'].sum().reset_index()
monthly_totals['duration'] = monthly_totals['duration']/60
opening_monthly_totals = monthly_totals

df["duration"] = pd.to_timedelta(df["duration"], unit='m')/1e9/60/60

fig = px.bar(df, x="month", y="duration", color=option[key],
        labels={
            "month": "",
            "duration": "durée d'ouverture / h",
            }
        )

for i, v in enumerate(monthly_totals['duration']):
    fig.add_annotation(
        x= monthly_totals.loc[i, 'month'],
        y= v + 1,  # Adjust y-position for better visibility
        text=f"{v}",
        showarrow=False,
    )
st.plotly_chart(fig)

# Plot income by machine
st.title('Revenus machines')
accounts = book.accounts.get(fullname="Chiffre d'affaire des ventes et prestations de services:Recettes:Heures machine").children
data = []
for account in accounts: 
    for split in account.splits:
        data.append({
            'date': split.transaction.post_date,
            'value': split.value,
            'account': str(split.account).split(':')[-1]
        })

df = pd.DataFrame(data)
df['value'] = -df['value']

# filter bouclement 
df = df[df['value']>0]

df['month'] = pd.to_datetime(df['date']).dt.strftime('%y-%m')
df['year'] = pd.to_datetime(df['date']).dt.strftime('%y')

# plot by month
result_df = df.groupby(['month', 'account'])['value'].sum().reset_index()
monthly_totals =df.groupby(['month'])['value'].sum().reset_index()
fig = px.bar(result_df, x='month', y='value', color='account', text_auto=True, title='Par mois')
st.plotly_chart(fig)

# plot by years
result_df = df.groupby(['year', 'account'])['value'].sum().reset_index()
yearly_totals =df.groupby(['year'])['value'].sum().reset_index()

fig = px.bar(result_df, x='year', y='value', color='account', title='Par année')

for i, v in enumerate(yearly_totals['value']):
    fig.add_annotation(
        x= yearly_totals.loc[i, 'year'],
        y= v + 300,  # Adjust y-position for better visibility
        text=f"{v}",
        showarrow=False,
    )

st.plotly_chart(fig)


df = monthly_totals.merge(opening_monthly_totals, how='inner', left_on='month', right_on='month')
df['ratio'] = pd.to_numeric(df['value']) / df['duration']

fig = px.bar(df, x='month', y='ratio', text_auto=True,
            labels={
            "month": "",
            "ratio": "Revenu par heure d'ouverture",
            }
)
st.plotly_chart(fig)

# Plot delta between reservation and start slot
st.title("Anticipation des utilisateurs.rices et superuser.rices")
df = df_machine_slot.merge(df_custom_user, how='inner', left_on='user', right_on='id')

df['delta'] = df['start'] - df['updated_at']

df = df[(df['delta'] > pd.Timedelta(seconds=0)) & (df['delta'] < pd.Timedelta(days=30))].dropna(subset=['user'])

df['delta_days'] =df['delta']/1e9/60/60/24
fig = px.histogram(df, x="delta_days", color='first_name', title="Distribution du temps entre la réservation et l'utilisation de la machine", nbins=30)
fig.update_layout(barmode='stack')
st.plotly_chart(fig)

# Plot delta between announcing openings and start openings as function of the superusers
df = df_opening_slot.merge(df_custom_user, how='inner', left_on='user', right_on='id')
df['delta'] = df['start'] - df['created_at']

df = df[(df['delta'] > pd.Timedelta(seconds=0)) & (df['delta'] < pd.Timedelta(days=30))]
df['delta_days'] =df['delta']/1e9/60/60/24
fig = px.histogram(df, x="delta_days", color='first_name', title="Distribution du temps entre la creation et de début de l'ouverture", nbins=30)
fig.update_layout(barmode='stack')
st.plotly_chart(fig)

# Plot subscription number
st.title('Abonnements')
df = df_subscription

# Define the date range (March 2023 to today)
start_date = pd.to_datetime('2023-03-01')
end_date = pd.to_datetime('today')

# Create a monthly date range
date_range = pd.date_range(start_date, end_date, freq='ME')

# Function to check if subscription is active on a specific date
def is_active(row, date):
  return (row['start'] <= date) & (row['end'] >= date)

# Calculate active subscriptions for each month
active_subscriptions = []
for date in date_range:
  active_count = df[df.apply(is_active, axis=1, date=date)].shape[0]
  active_subscriptions.append(active_count)

# Create DataFrame with results
result_df = pd.DataFrame({'Date': date_range, 'Active Subscriptions': active_subscriptions})
result_df['month'] = result_df['Date'].dt.strftime('%y-%m')
fig = px.bar(result_df, x='month', y='Active Subscriptions', text_auto=True)
st.plotly_chart(fig)

# Plot Subscription
st.title('Revenus abonnement')
account = book.accounts.get(fullname="Chiffre d'affaire des ventes et prestations de services:Recettes:Cotisations")
data = []
for split in account.splits:
    data.append({
        'date': split.transaction.post_date,
        'value': split.value,
        'account': str(split.account).split(':')[-1]
    })

df = pd.DataFrame(data)
df['value'] = -df['value']

# filter bouclement
df = df[df['value']>0]

df['year'] = pd.to_datetime(df['date']).dt.strftime('%y')
result_df = df.groupby(['year'])['value'].sum().reset_index()
fig = px.bar(result_df, x='year', y='value', text_auto=True)

st.plotly_chart(fig)