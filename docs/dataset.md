# Dataset Documentation

## Dataset Source

The dataset is stored in:

- `Dataset/FlightPrice.csv`

A secondary location is supported in the ML loader at:

- `data/raw/FlightPrice.csv`

## Data Dictionary

| Column | Type | Description |
|---|---|---|
| Airline | string | Airline name for the flight |
| Date_of_Journey | string | Journey date in `DD/MM/YYYY` format |
| Source | string | Departure city |
| Destination | string | Arrival city |
| Route | string | Flight route details (e.g. city transit path) |
| Dep_Time | string | Departure time in `HH:MM` format |
| Arrival_Time | string | Arrival time in `HH:MM` format |
| Duration | string | Total flight duration (e.g. `2h 50m`) |
| Total_Stops | string | Number of stops (e.g. `non-stop`, `1 stop`) |
| Additional_Info | string | Supplemental flight details |
| Price | integer | Ticket price in INR |

## Schema and Preprocessing

### Key derived features

The feature engineering pipeline converts the dataset into these numeric fields:

- `day` — day of month extracted from `Date_of_Journey`
- `month` — month extracted from `Date_of_Journey`
- `year` — year extracted from `Date_of_Journey`
- `day_of_week` — weekday index derived from the journey date
- `dep_hour` — departure hour extracted from `Dep_Time`
- `dep_minute` — departure minute extracted from `Dep_Time`
- `arrival_hour` — arrival hour extracted from `Arrival_Time`
- `arrival_minute` — arrival minute extracted from `Arrival_Time`
- `duration_minutes` — duration expressed as total minutes
- `Total_Stops` — numeric stop count parsed from `Total_Stops`
- `Airline`, `Source`, `Destination`, `Additional_Info` are label-encoded

### Columns dropped before training

- `Date_of_Journey`
- `Dep_Time`
- `Arrival_Time`
- `Duration`
- `Route`

## Dataset quality notes

- `Price` is the target variable.
- Missing values are handled by the feature engineering process.
- Categorical values are normalized and label-encoded.
- Clean `Additional_Info` is replaced with `No info` when missing.
