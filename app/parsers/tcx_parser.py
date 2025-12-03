import xml.etree.ElementTree as ET

def parse_tcx_file(tcx_content):
    """
    Parsing semplificato dei file TCX Garmin.
    Estrae le informazioni principali:
      - data dell'attività
      - lista step Garmin Coach (se presenti)
      - traccia (tempo, distanza, HR, cadenza, velocità)
    """
    root = ET.fromstring(tcx_content)

    ns = {
        "tcx": "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"
    }

    # -------------------------------
    # DATA ATTIVITÀ
    # -------------------------------
    activity = root.find(".//tcx:Activity", ns)
    if activity is None:
        raise ValueError("TCX non contiene dati Activity")

    activity_date = activity.get("StartTime", None)

    # -------------------------------
    # TRACKPOINTS
    # -------------------------------
    trackpoints = []

    for tp in root.findall(".//tcx:Trackpoint", ns):
        tp_data = {}

        time_el = tp.find("tcx:Time", ns)
        dist_el = tp.find("tcx:DistanceMeters", ns)
        hr_el = tp.find(".//tcx:HeartRateBpm/tcx:Value", ns)
        cad_el = tp.find("tcx:Cadence", ns)
        speed_el = tp.find("tcx:Extensions/tcx:TPX/tcx:Speed", ns)

        if time_el is not None:
            tp_data["time"] = time_el.text

        if dist_el is not None:
            tp_data["distance_m"] = float(dist_el.text)

        if hr_el is not None:
            tp_data["hr"] = int(hr_el.text)

        if cad_el is not None:
            tp_data["cadence"] = int(cad_el.text)

        if speed_el is not None:
            tp_data["speed_m_s"] = float(speed_el.text)

        trackpoints.append(tp_data)

    # -------------------------------
    # STEPS GARMIN COACH (se presenti)
    # -------------------------------
    steps = []

    for step in root.findall(".//tcx:Step", ns):
        step_data = {}

        step_type = step.get("Type")
        step_name = step.get("Name")

        duration_el = step.find("tcx:Duration", ns)
        target_el = step.find("tcx:Target", ns)

        if step_type:
            step_data["type"] = step_type

        if step_name:
            step_data["name"] = step_name

        if duration_el is not None:
            step_data["duration_seconds"] = float(duration_el.text)

        if target_el is not None:
            step_data["target"] = target_el.text

        steps.append(step_data)

    # -------------------------------
    # JSON OUTPUT
    # -------------------------------
    result = {
        "date": activity_date,
        "summary": {
            "total_trackpoints": len(trackpoints),
        },
        "steps": steps,
        "track": trackpoints
    }

    return result
