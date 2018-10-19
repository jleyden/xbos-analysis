import pandas as pd
import pytz
from pandas.tseries.holiday import USFederalHolidayCalendar as calendar
import time
import datetime
import enum
import numpy as np

from collect import get_weather_power_tstat
import df_utils as du
import baseline as bl
from get_greenbutton_id import get_greenbutton_id

# Some functions for sampling from the csv

def event_table(site, event_day, baseline_start, baseline_end, event_start_h=14, event_end_h=18):
    meter_id = get_greenbutton_id(site, baseline_start, baseline_end)
    meter_id = meter_id[0] # need a better way to aggregate meters
    event_day = pd.Timestamp(event_day)
    baseline_start_ts = pd.to_datetime(baseline_start)
    baseline_end_ts = pd.to_datetime(baseline_end)
    data = get_weather_power_tstat(site, baseline_start, baseline_end)
    power_gb = du.process_df(data['power'].df) * 4
    power_15min=power_gb[power_gb.index < event_day + pd.Timedelta(days=1)]
    site_df, site_name = du._configure_MDAL_df(site, data, power_15min, meter_id)
    weather = du.process_df(data['weather'].df, Nmin="1h") 

    baseline_temp=[]
    baseline_demand_3=[]
    baseline_cooling=[]
    baseline_heating=[]
    baseline_weather=[]
    X=3
    index_list=[]

    site = site_name
    weather['mean'] = weather.mean(axis=1)
    weather_site = weather['mean']
    weather_site=weather_site.to_frame()
    weather_site.columns=["OAT_Event"] #adjust collumn name to show up in legend properly

    data = site_df
    demand, temperature, heating, cooling = bl._select_demand(data)
    demand_pivot = bl._create_pivot(demand)
    temperature_pivot = bl._create_pivot(temperature)
    heating_pivot = bl._create_pivot(heating)
    cooling_pivot = bl._create_pivot(cooling)
    weather_pivot= bl._create_pivot(weather_site, freq='1h')
    demand_baseline, days, event_data, x_days= bl.get_X_in_Y_baseline(demand_pivot,
                        event_day,
                        X=X,
                        Y=10, 
                        event_start_h=event_start_h,
                        event_end_h=event_end_h, 
                        adj_ratio=True,
                        min_ratio=1.0, 
                        max_ratio=1.2,
                        sampling="quarterly")
    event_demand = demand_pivot[demand_pivot.index==event_day].T
    baseline_demand_3.append(demand_baseline.T)
    index_list.append(site)
    
    event_index=(str(event_day))[0:10]
    weather_site=weather_site[event_index:event_index]
    weather_event=weather_site
    weather_event=weather_event.set_index("hour")

    weather_baseline=bl.make_baseline(x_days, event_day, weather_pivot, name="OAT_Baseline", freq="1h")

    #IAT Temperature baseline
    temperature_baseline=bl.make_baseline(x_days, event_day, temperature_pivot, name="IAT_Baseline")
    event_temperature = temperature_pivot[temperature_pivot.index==event_day].T

    weather_baseline_15min = np.repeat(weather_baseline['OAT_Baseline'], 4)
    weather_event_15min = np.repeat(weather_event['OAT_Event'], 4)

    event_table = pd.DataFrame({
        'baseline-demand': demand_baseline.iloc[:, 0],
        'event-demand': event_demand.iloc[:, 0],
        'baseline-weather': weather_baseline_15min.values,
        'event-weather': weather_event_15min.values,
        'baseline-IAT': temperature_baseline.values,
        'event-IAT': event_temperature.iloc[:, 0]
    })

    return event_table


