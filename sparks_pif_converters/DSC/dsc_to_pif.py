import csv
import argparse
from pypif import pif
from pypif.obj import *
import peakutils
import os
import re

def netzsch_3500_to_pif(closed_csv):
    print("FILE IDENTIFIED AS NETZSCH 3500 OUTPUT FILE: %s" % closed_csv)

    # create chemical system and property array
    my_pif = ChemicalSystem()
    my_pif.ids = [os.path.basename(closed_csv).split("_")[0]]
    my_pif.properties = []

    # Store index so that iteration can start at next row. Default to False when no header is found.
    header_row_index = False

    # Initialize arrays for heat capacity and conditions (time and temp)
    temp_array = []
    time_array = []
    heat_capacity_array = []

    # open csv, iterate through rows.
    with open(closed_csv, 'rU') as open_csv:
        reader = csv.reader(open_csv)
        for index, row in enumerate(reader):

            # ensure row has values
            if len(row) == 0:
                continue

            # set values based on row[0]
            if '#IDENTITY:' in row[0]:
                my_pif.chemical_formula = row[1].strip()

            if "#INSTRUMENT:" in row[0]:
                measurement_device = Instrument(name=row[1].split(" ")[0], model=row[1].split(" ")[2])

            if "#SAMPLE MASS /mg:" in row[0]:
                prop = Property(name='sample mass', scalars=row[1], units='mg')
                my_pif.properties.append(prop)

            if "#DATE/TIME:" in row[0]:
                date = Value(name="Experiment date", scalars=row[1].strip())

            if "#TYPE OF CRUCIBLE:" in row[0]:
                crucible = Value(name="Crucible", scalars=row[1].strip()+" "+row[2].strip())

            if "#PROTECTIVE GAS:" in row[0]:
                atmosphere = Value(name="Atmosphere", scalars=row[1].strip())

            if "#RANGE:" in row[0]:
                heating_rate = Value(name="Heating rate", scalars=row[1].split("/")[1].split("(")[0], units="K/min")

            # Temp indicates header row. Define header_row_index.
            if '##Temp.' in row[0]:
                header_row_index = index

            # Iterate through values after header_row.
            if header_row_index:
                if index > header_row_index:
                    temp_array.append(float(row[0]))
                    time_array.append(float(row[1]))
                    heat_capacity_array.append(float(row[2]))

    float_capacities = [float(h) for h in heat_capacity_array]
    peak_indexes = peakutils.peak.indexes(float_capacities, thres=0.35/max(float_capacities), min_dist=1)
    # if peaks are located, add the phase transition property
    if len(peak_indexes) > 0:
        dsc_phase_transition = Property(name='Temperature of Phase Transition', scalars=str(temp_array[peak_indexes[0]]), units='$^\circ$C')
        my_pif.properties.append(dsc_phase_transition)

    # define property and append scalar values
    heat_capacity = Property('C$_p$', scalars=heat_capacity_array, units='J/(gK)')
    temp = Value(name='Temperature', scalars=temp_array, units='$^\circ$C')
    time = Value(name='Time', scalars=time_array, units='min')

    # append conditions.
    heat_capacity.conditions = [temp, date, crucible, atmosphere, heating_rate]
    heat_capacity.instrument = measurement_device
    heat_capacity.files = FileReference(relative_path=os.path.basename(closed_csv))

    # append property to pif
    my_pif.properties.append(heat_capacity)

    # print dump to check format
    # print(pif.dumps(my_pif, indent=4))

    return my_pif


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('csv', nargs='*', help='path to DSC csv')

    args = parser.parse_args()

    for f in args.csv:
        print("PARSING: {}".format(f))
        pifs = netzsch_3500_to_pif(f)
        f_out = f.replace(".csv", ".json")
        print("OUTPUT FILE: {}").format(f_out)
        pif.dump(pifs, open(f_out, "w"), indent=4)