; ===========================================================
; disease-symptoms.clp
; Auto-generated from knowledge_base.json on 2026-11-09T22:53:50.260884
; DO NOT EDIT DIRECTLY — edit knowledge_base.json and re-run generate_clp.py
; This is for academic demonstration only.
; ===========================================================

; --- Core templates ---

(deftemplate symptom
  "A symptom reported by the user"
  (slot name (type SYMBOL)))

(deftemplate disease-profile
  "A disease entry from the knowledge base"
  (slot id (type SYMBOL))
  (slot name (type STRING))
  (slot category (type SYMBOL))
  (slot severity (type SYMBOL))
  (multislot symptoms))

(deftemplate candidate
  "A candidate disease with match counts"
  (slot name (type STRING))
  (slot id (type SYMBOL))
  (slot matched (type INTEGER) (default 0))
  (slot total (type INTEGER) (default 0))
  (slot category (type SYMBOL))
  (slot severity (type SYMBOL)))

(deftemplate confirmed-disease
  "A disease that has high confidence"
  (slot name (type STRING))
  (slot id (type SYMBOL))
  (slot confidence (type FLOAT)))

(deftemplate emergency
  "An emergency condition detected"
  (slot message (type STRING))
  (slot priority (type INTEGER) (default 100)))

(deftemplate diagnosis-complete
  "Signal that diagnosis is done"
  (slot status (type SYMBOL)))

; --- Disease knowledge base facts ---

(deffacts disease-knowledge
  "All diseases in the knowledge base"
  (disease-profile
    (id d046)
    (name "Curl Demo Syndrome")
    (category respiratory)
    (severity moderate)
    (symptoms brittle_nails bleeding_gums increased_sweating bad_breath))
  (disease-profile
    (id d001)
    (name "Common Cold")
    (category respiratory)
    (severity mild)
    (symptoms runny_nose sneezing sore_throat cough nasal_congestion fatigue mild_fever))
  (disease-profile
    (id d002)
    (name "Influenza")
    (category respiratory)
    (severity moderate)
    (symptoms fever chills severe_headache muscle_pain fatigue dry_cough sore_throat runny_nose weakness))
  (disease-profile
    (id d003)
    (name "COVID-like Respiratory Illness")
    (category respiratory)
    (severity moderate)
    (symptoms fever dry_cough fatigue loss_of_taste loss_of_smell shortness_of_breath headache muscle_pain sore_throat chills))
  (disease-profile
    (id d004)
    (name "Migraine")
    (category neurological)
    (severity moderate)
    (symptoms severe_headache nausea vomiting sensitivity_to_light sensitivity_to_sound blurred_vision dizziness throbbing_pain))
  (disease-profile
    (id d005)
    (name "Tension Headache")
    (category neurological)
    (severity mild)
    (symptoms headache neck_pain fatigue sensitivity_to_light muscle_tension pressure_around_head))
  (disease-profile
    (id d006)
    (name "Gastroenteritis")
    (category digestive)
    (severity mild)
    (symptoms nausea vomiting diarrhea abdominal_pain fever muscle_pain dehydration loss_of_appetite))
  (disease-profile
    (id d007)
    (name "Typhoid Fever")
    (category general_systemic)
    (severity severe)
    (symptoms fever weakness abdominal_pain headache diarrhea constipation rash loss_of_appetite muscle_pain enlarged_spleen))
  (disease-profile
    (id d008)
    (name "Malaria")
    (category general_systemic)
    (severity severe)
    (symptoms fever chills increased_sweating headache muscle_pain fatigue nausea vomiting pallor rapid_heartbeat))
  (disease-profile
    (id d009)
    (name "Dengue Fever")
    (category general_systemic)
    (severity severe)
    (symptoms fever severe_headache muscle_pain joint_pain rash eye_pain nausea vomiting fatigue bleeding_gums bruising))
  (disease-profile
    (id d010)
    (name "Pneumonia")
    (category respiratory)
    (severity severe)
    (symptoms fever productive_cough chest_pain shortness_of_breath chills fatigue rapid_breathing confusion))
  (disease-profile
    (id d011)
    (name "Bronchitis")
    (category respiratory)
    (severity mild)
    (symptoms productive_cough chest_tightness fatigue fever shortness_of_breath wheezing sore_throat nasal_congestion))
  (disease-profile
    (id d012)
    (name "Asthma")
    (category respiratory)
    (severity moderate)
    (symptoms wheezing shortness_of_breath chest_tightness cough rapid_breathing difficulty_breathing_at_night))
  (disease-profile
    (id d013)
    (name "Hypertension")
    (category cardiovascular)
    (severity moderate)
    (symptoms headache dizziness blurred_vision chest_pain shortness_of_breath nosebleed palpitations fatigue))
  (disease-profile
    (id d014)
    (name "Type 2 Diabetes")
    (category general_systemic)
    (severity moderate)
    (symptoms excessive_thirst frequent_urination excessive_hunger fatigue blurred_vision poor_wound_healing numbness tingling weight_loss high_blood_sugar))
  (disease-profile
    (id d015)
    (name "Anemia")
    (category general_systemic)
    (severity mild)
    (symptoms fatigue weakness pallor shortness_of_breath dizziness cold_extremities chest_pain headache rapid_heartbeat pale_skin))
  (disease-profile
    (id d016)
    (name "Urinary Tract Infection")
    (category urinary)
    (severity mild)
    (symptoms painful_urination burning_urination frequent_urination urinary_urgency cloudy_urine blood_in_urine pelvic_pain fever lower_back_pain))
  (disease-profile
    (id d017)
    (name "GERD (Acid Reflux)")
    (category digestive)
    (severity mild)
    (symptoms heartburn acid_reflux chest_pain difficulty_swallowing sour_taste nausea regurgitation hoarseness chronic_cough))
  (disease-profile
    (id d018)
    (name "Appendicitis")
    (category digestive)
    (severity severe)
    (symptoms abdominal_pain nausea vomiting fever loss_of_appetite rebound_tenderness abdominal_rigidity migration_of_pain_to_right_lower_quadrant))
  (disease-profile
    (id d019)
    (name "Jaundice")
    (category digestive)
    (severity moderate)
    (symptoms jaundice dark_urine pale_stools fatigue abdominal_pain nausea loss_of_appetite fever itching yellowing_of_skin))
  (disease-profile
    (id d020)
    (name "Chickenpox")
    (category skin)
    (severity mild)
    (symptoms rash blisters itching fever fatigue loss_of_appetite headache skin_peeling))
  (disease-profile
    (id d021)
    (name "Allergic Rhinitis")
    (category eye_ent)
    (severity mild)
    (symptoms sneezing runny_nose nasal_congestion itching watery_eyes eye_redness fatigue postnasal_drip cough))
  (disease-profile
    (id d022)
    (name "Sinusitis")
    (category eye_ent)
    (severity mild)
    (symptoms facial_pain nasal_congestion headache fever loss_of_smell toothache fatigue postnasal_drip cough sore_throat))
  (disease-profile
    (id d023)
    (name "Tonsillitis")
    (category eye_ent)
    (severity mild)
    (symptoms sore_throat fever difficulty_swallowing swollen_lymph_nodes headache bad_breath voice_changes fatigue ear_pain))
  (disease-profile
    (id d024)
    (name "Conjunctivitis (Pink Eye)")
    (category eye_ent)
    (severity mild)
    (symptoms eye_redness eye_discharge eye_pain watery_eyes itching sensitivity_to_light blurred_vision swollen_eyelids))
  (disease-profile
    (id d025)
    (name "Rheumatoid Arthritis")
    (category musculoskeletal)
    (severity moderate)
    (symptoms joint_pain swollen_joints stiffness fatigue fever loss_of_appetite muscle_pain joint_warmth morning_stiffness))
  (disease-profile
    (id d026)
    (name "Osteoarthritis")
    (category musculoskeletal)
    (severity mild)
    (symptoms joint_pain stiffness swollen_joints bone_pain muscle_weakness reduced_range_of_motion joint_cracking))
  (disease-profile
    (id d027)
    (name "Peptic Ulcer")
    (category digestive)
    (severity moderate)
    (symptoms abdominal_pain heartburn nausea bloating loss_of_appetite blood_in_stool vomiting dark_stools weight_loss))
  (disease-profile
    (id d028)
    (name "Irritable Bowel Syndrome")
    (category digestive)
    (severity mild)
    (symptoms abdominal_pain bloating diarrhea constipation excessive_gas mucus_in_stool nausea fatigue))
  (disease-profile
    (id d029)
    (name "Hypothyroidism")
    (category general_systemic)
    (severity mild)
    (symptoms fatigue weight_gain cold_extremities constipation dry_skin hair_loss depression muscle_weakness memory_loss bradycardia))
  (disease-profile
    (id d030)
    (name "Hyperthyroidism")
    (category general_systemic)
    (severity moderate)
    (symptoms weight_loss rapid_heartbeat palpitations increased_sweating tremors fatigue anxiety heat_intolerance diarrhea muscle_weakness))
  (disease-profile
    (id d031)
    (name "Kidney Stone")
    (category urinary)
    (severity severe)
    (symptoms severe_back_pain painful_urination blood_in_urine nausea vomiting frequent_urination fever cloudy_urine urinary_urgency))
  (disease-profile
    (id d032)
    (name "Acute Myocardial Infarction (Heart Attack)")
    (category cardiovascular)
    (severity severe)
    (symptoms chest_pain shortness_of_breath increased_sweating nausea vomiting dizziness left_arm_pain jaw_pain palpitations cold_extremities))
  (disease-profile
    (id d033)
    (name "Stroke")
    (category neurological)
    (severity severe)
    (symptoms facial_drooping arm_weakness slurred_speech confusion severe_headache vision_loss dizziness loss_of_coordination numbness))
  (disease-profile
    (id d034)
    (name "Meningitis")
    (category neurological)
    (severity severe)
    (symptoms severe_headache stiff_neck fever sensitivity_to_light sensitivity_to_sound nausea vomiting rash confusion seizures))
  (disease-profile
    (id d035)
    (name "Hepatitis B")
    (category digestive)
    (severity severe)
    (symptoms jaundice fatigue abdominal_pain nausea vomiting dark_urine pale_stools fever joint_pain loss_of_appetite))
  (disease-profile
    (id d036)
    (name "Eczema (Atopic Dermatitis)")
    (category skin)
    (severity mild)
    (symptoms itching rash redness dry_skin blisters skin_peeling thickened_skin swollen_areas))
  (disease-profile
    (id d037)
    (name "Psoriasis")
    (category skin)
    (severity mild)
    (symptoms rash itching skin_peeling redness joint_pain dry_skin silvery_scales thickened_skin))
  (disease-profile
    (id d038)
    (name "Anaphylaxis")
    (category general_systemic)
    (severity severe)
    (symptoms hives shortness_of_breath swelling_of_throat dizziness low_blood_pressure rapid_heartbeat nausea vomiting confusion loss_of_consciousness))
  (disease-profile
    (id d039)
    (name "Panic Disorder")
    (category neurological)
    (severity mild)
    (symptoms palpitations chest_pain shortness_of_breath dizziness increased_sweating tremors numbness tingling nausea feeling_of_doom))
  (disease-profile
    (id d040)
    (name "Gout")
    (category musculoskeletal)
    (severity moderate)
    (symptoms joint_pain swollen_joints redness joint_warmth fever intense_pain_in_big_toe limited_range_of_motion fatigue))
  (disease-profile
    (id d041)
    (name "Scabies")
    (category skin)
    (severity mild)
    (symptoms intense_itching rash blisters burrow_marks itching_worse_at_night redness skin_sores))
  (disease-profile
    (id d042)
    (name "Peptic Ulcer Disease (Bleeding)")
    (category digestive)
    (severity severe)
    (symptoms blood_in_stool vomiting_blood dark_stools abdominal_pain dizziness weakness rapid_heartbeat low_blood_pressure))
  (disease-profile
    (id d043)
    (name "Anxiety Disorder")
    (category neurological)
    (severity mild)
    (symptoms anxiety excessive_worry fatigue muscle_tension headache difficulty_concentrating sleep_disturbance irritability palpitations))
  (disease-profile
    (id d044)
    (name "Dehydration")
    (category general_systemic)
    (severity moderate)
    (symptoms extreme_thirst dark_urine decreased_urine_output dizziness fatigue dry_mouth headache confusion rapid_heartbeat low_blood_pressure))
  (disease-profile
    (id d045)
    (name "Iron Deficiency Anemia")
    (category general_systemic)
    (severity mild)
    (symptoms fatigue weakness pallor shortness_of_breath cold_extremities headache brittle_nails hair_loss dizziness pale_skin))
)

; --- Emergency / Safety Rules (salience 1000) ---

(defrule detect-cardiac-emergency
  "Emergency: cardiac-emergency"
  (declare (salience 1000))
  (symptom (name chest_pain))
  (symptom (name shortness_of_breath))
  (symptom (name increased_sweating))
  =>
  (assert (emergency (message "Possible cardiac emergency (chest pain + breathlessness + sweating). Call emergency services immediately!"))))

(defrule detect-stroke-emergency
  "Emergency: stroke-emergency"
  (declare (salience 1000))
  (symptom (name facial_drooping))
  (symptom (name arm_weakness))
  (symptom (name slurred_speech))
  =>
  (assert (emergency (message "Possible stroke (FAST: Face drooping, Arm weakness, Speech difficulty). Call emergency services immediately!"))))

(defrule detect-meningitis-emergency
  "Emergency: meningitis-emergency"
  (declare (salience 1000))
  (symptom (name severe_headache))
  (symptom (name stiff_neck))
  (symptom (name fever))
  =>
  (assert (emergency (message "Possible meningitis (severe headache + stiff neck + fever). Seek emergency care immediately!"))))

(defrule detect-anaphylaxis-emergency
  "Emergency: anaphylaxis-emergency"
  (declare (salience 1000))
  (symptom (name hives))
  (symptom (name shortness_of_breath))
  (symptom (name rapid_heartbeat))
  =>
  (assert (emergency (message "Possible anaphylaxis (severe allergic reaction). Use epinephrine auto-injector and call emergency services!"))))

(defrule detect-gi-bleed-emergency
  "Emergency: gi-bleed-emergency"
  (declare (salience 1000))
  (symptom (name vomiting_blood))
  (symptom (name dark_stools))
  =>
  (assert (emergency (message "Possible gastrointestinal bleeding (vomiting blood or black stools). Seek emergency care immediately!"))))

(defrule detect-appendicitis-emergency
  "Emergency: appendicitis-emergency"
  (declare (salience 1000))
  (symptom (name abdominal_pain))
  (symptom (name fever))
  (symptom (name rebound_tenderness))
  =>
  (assert (emergency (message "Possible appendicitis. Seek emergency surgical evaluation immediately!"))))

(defrule detect-seizure-emergency
  "Emergency: seizure-emergency"
  (declare (salience 1000))
  (symptom (name seizures))
  =>
  (assert (emergency (message "Seizure detected. Seek emergency care immediately if this is a new onset seizure!"))))

(defrule detect-low-consciousness-emergency
  "Emergency: low-consciousness-emergency"
  (declare (salience 1000))
  (symptom (name confusion))
  (symptom (name low_blood_pressure))
  (symptom (name rapid_heartbeat))
  =>
  (assert (emergency (message "Possible shock or severe systemic illness. Seek emergency care immediately!"))))

; --- General Matching Rule ---

(defrule compute-candidates
  "For each disease-profile, count how many asserted symptoms it contains"
  (declare (salience 10))
  (disease-profile (id ?id) (name ?n) (symptoms $?syms) (category ?cat) (severity ?sev))
  =>
  (bind ?matched 0)
  (bind ?total (length$ ?syms))
  (progn$ (?s ?syms)
    (if (any-factp ((?f symptom)) (eq ?f:name ?s))
      then (bind ?matched (+ ?matched 1))))
  (if (> ?matched 0)
    then (assert (candidate (name ?n) (id ?id) (matched ?matched) (total ?total) (category ?cat) (severity ?sev)))))

(defrule confirm-high-confidence
  "Assert confirmed-disease for high confidence matches (>= 70%)"
  (declare (salience 5))
  ?c <- (candidate (name ?n) (id ?id) (matched ?m) (total ?t))
  (test (>= (/ ?m ?t) 0.7))
  =>
  (assert (confirmed-disease (name ?n) (id ?id) (confidence (/ ?m ?t)))))

(defrule mark-complete
  "Signal diagnosis computation is complete"
  (declare (salience -100))
  =>
  (assert (diagnosis-complete (status done))))

; End of generated CLIPS knowledge base