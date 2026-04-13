clinic_Data = {
    "Dr. Neha Verma" : {
        "specialization" : "Pediatrician ",
        "available_day" : ["Monday", "Wednesday", "Friday"],
        "available_time" : [11 , 12 , 1 , 2 , 3 , 4],
        "consultation_charges" : "700"
    },
    "Dr. Priya Mehta" : {
        "specialization" : "Gynecologist",
        "available_day" : ["Tuesday", "Thursday" ,"Saturday"],
        "available_time" : [12 , 1 , 2 ,3 , 4 , 5],
        "consultation_charges" : "800"
    },
    "Dr. Rahul Sharma" : {
        "specialization" : "Dermatologist",
        "available_day" : ["Monday", "Tuesday", "Wednesday", "Tuesday" ,"Friday"],
        "available_time" : [5 ,6 ,7, 8],
        "consultation_charges" : "900"
    },
    "Dr. Karan Patel" : {
        "specialization" : "Dentist",
        "available_day" : ["Monday", "Tuesday", "Wednesday", "Tuesday" ,"Friday" , "Saturday"],
        "available_time" : [9, 10, 11, 12 , 1],
        "consultation_charges" : "600"
    }
}


if __name__ == "__main__":
    print(clinic_Data['Dr. Neha Verma']['specialization'])