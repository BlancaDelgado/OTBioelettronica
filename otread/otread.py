import os
import pathlib
import warnings
import tarfile
import tempfile
import xml.etree.ElementTree as ET
import numpy as np
import yaml


def otread(pathname: str, filename: str) -> None:
    """
    OTREAD Reads .otb+ file and exports data to .csv file and headers to .yaml file.
    The data from .otb+ file is extracted to a temporary folder; headers of LoaderOTComm signals are read from
    <form_dock00.xml> .otb+ file and data is read from the corresponding .sig file. Then, headers (i.e.,
    track_index, description, unity_of_measurement, power_supply, fsample, ad_bits, signal_gain, low_pass_filter,
    high_pass_filter) are stored in a .yaml file and data (i.e., one column per signal according to track_index, and
    time corresponding to the last column) is stored in a .csv file.

    NOTE: if .csv or .yaml file already exists for .otb+ file, the .otb+ file is not analysed.
    NOTE: in MATLAB, you can use extension yaml (e.g., version 1.5.4.0) to read headers: yaml.loadFile("file.yaml")

    :param pathname: path to directory containing .otb+ file.
    :param filename: name of .otb+ file.

    Created by Blanca Delgado Bonet (blancadelgadobonet@cajal.csic.es)
    June 2023, last edit: 2023-06-14
    """

    # Check that output files do not exist already:
    p1 = os.path.join(pathname, filename.replace(".otb+", ".yaml"))
    p2 = os.path.join(pathname, filename.replace(".otb+", ".csv"))
    if os.path.exists(p1) or os.path.exists(p2):
        raise Exception(f"({filename}) Converted files already exist; file is not processed to avoid overwriting.")

    # Download OTB+ files in a temporal directory:
    with tempfile.TemporaryDirectory() as PATHTEMP:
        print(f"Created temporary directory to extract OTB+ signals at: {PATHTEMP}")
    
        # Extract OTB+ signals:
        otb_record = tarfile.open(os.path.join(pathname, filename))
        otb_record.extractall(PATHTEMP)
        print(f"OTB+ files: {os.listdir(PATHTEMP)}")
    
        # READ HEADERS
        xml_record = ET.parse(os.path.join(PATHTEMP, "form_dock00.xml"))
        root = xml_record.getroot()
    
        n_signals = 0
        headers = {"track_index": [], "description": [], "unity_of_measurement": [], "power_supply": [], "fsample": [],
                   "ad_bits": [], "signal_gain": [], "low_pass_filter": [], "high_pass_filter": []}
        for signal in root.iter("signal"):
    
            # Select acquired signals only:
            # <plugin>: LoaderOTComm (for acquired signals), LoaderProcessing (for OTB real time processing)
            if signal.find("plugin").text == "LoaderOTComm":
                n_signals += 1
                # Get headers:
                headers["power_supply"].append(5)  # force value (according to previous MATLAB script)
                for key in headers.keys() - ["power_supply"]:  # look for values
                    val = signal.find(key)
                    if val is not None:
                        val = val.text
                    headers[key].append(val)  # if element was found keep text associated to tag, else keep None
    
                # Common parameters to all LoaderOTComm signals:
                if n_signals == 1:
                    signal_path = signal.find("signal_path")
                    track_totalnumber = signal.find("track_totalnumber")
                    timestep = 1 / float(headers["fsample"][0])
    
        # READ SIGNALS
        if None not in [signal_path, track_totalnumber]:
    
            heads = ["track_index", "power_supply", "fsample", "ad_bits", "signal_gain",
                     "low_pass_filter", "high_pass_filter"]
            types = [int, float, float, int, float, float, float]
            for h, t in zip(heads, types):
                headers[h] = np.array(headers[h], dtype=t)
    
            signal_path = signal_path.text
            track_totalnumber = int(track_totalnumber.text)
    
            # Open file with data:
            with open(os.path.join(PATHTEMP, signal_path), mode='rb') as file:
                data = file.read()  # read (only) bytes
                data = np.frombuffer(data, dtype=np.int16)  # transform bytes to integers
                data = data.copy().astype(float)
    
            # Adapt data format:
            data = np.reshape(data, (-1, track_totalnumber))  # reshape values according to the total number of signals
            data = data[:, headers["track_index"]]  # select LoaderOTComm signals
    
            for n in range(n_signals):
                # Get factor according to units of signal (so that all recovered signals are returned in V):
                if headers["unity_of_measurement"][n] == "mV":
                    factor = 1000
                elif headers["unity_of_measurement"][n] == "V":
                    factor = 1
                else:
                    raise Exception("Unity of measurement was not recognized (only mV and V are predefined); "
                                    "include your corresponding factor according to the unity of measurement.")
    
                # Get true signal (according to previous MATLAB script):
                data[:, n] = data[:, n] * headers["power_supply"][n] / (2**headers["ad_bits"][n]) * factor / headers["signal_gain"][n]
    
            # Append time column:
            time = np.arange(data.shape[0]) * timestep
            data = np.column_stack([data, time.T])
    
            # Save headers:
            for h in heads:
                headers[h] = headers[h].tolist()
    
            with open(os.path.join(pathname, filename.replace(".otb+", ".yaml")), 'w') as file:
                yaml.dump(headers, file)
    
            # Save data:
            np.savetxt(os.path.join(pathname, filename.replace(".otb+", ".csv")), data, delimiter=',')
            
    return


if __name__ == "__main__":

    PATH = "/Users/blancadelgado/Library/CloudStorage/OneDrive-UniversidadReyJuanCarlos/2022-23 CSIC/01 DATA/SUBJECTS"
    for path in pathlib.Path(PATH).glob('**/*.otb+'):

        PATHNAME, FILENAME = os.path.split(path)
        try:
            otread(PATHNAME, FILENAME)
        except:
            warnings.warn(f"Could not analyse {FILENAME}")
