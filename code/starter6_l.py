import pickle
import pandas as pd
import os
import argparse

def load_model():
    with open('model.bin', 'rb') as f_in:
        dv, lr = pickle.load(f_in)
    return dv, lr


def get_paths(year, month):
    filepath = f"fhv_tripdata_{year:04d}-{month:02d}.parquet"
    fname = os.path.basename(filepath)
    os.system(f'wget https://nyc-tlc.s3.amazonaws.com/trip+data/{fname}')


    input_file = filepath
    output_file = f'output_{os.path.basename(filepath)}'

    return input_file, output_file

def read_data(filename):
    df = pd.read_parquet(filename)
    
    df['duration'] = df.dropOff_datetime - df.pickup_datetime
    df['duration'] = df.duration.dt.total_seconds() / 60

    df = df[(df.duration >= 1) & (df.duration <= 60)].copy()
    categorical = ['PUlocationID', 'DOlocationID']

    df[categorical] = df[categorical].fillna(-1).astype('int').astype('str')
    
    return df




def save_results(df, y_pred, output_file):
    df_result = pd.DataFrame()
    df_result['ride_id'] = df['ride_id']
    df_result['predicted_duration'] = y_pred

    df_result.to_parquet(
        output_file,
        engine='pyarrow',
        compression=None,
        index=False
        )



def run():
    parser = argparse.ArgumentParser()

    
    parser.add_argument(
        "--year",
        type=int,
        default=2021,
        help="trip year (default: 2021)",
    )

    parser.add_argument(
        "--month",
        type=int,
        default=3,
        help="trip month (default: 3)",
    )
    args, _ = parser.parse_known_args()

    input_file, output_file = get_paths(args.year, args.month)

    df = read_data(input_file)
    df['ride_id'] = f'{args.year:04d}/{args.month:02d}_' + df.index.astype('str')
    categorical = ['PUlocationID', 'DOlocationID']
    dicts = df[categorical].to_dict(orient='records')
    dv, lr = load_model()
    X_val = dv.transform(dicts)
    y_pred = lr.predict(X_val)
    mean_pred_duration = y_pred.mean()
    print(mean_pred_duration)
    save_results(df, y_pred, output_file)


if __name__ == '__main__':
    run()

