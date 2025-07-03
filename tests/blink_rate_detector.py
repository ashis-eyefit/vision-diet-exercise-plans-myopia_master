import cv2
import dlib
from scipy.spatial import distance

## Costants

RIGHT_EYE = [36, 37, 38, 39, 40, 41]
LEFT_EYE = [42, 43, 44, 45, 46, 47]
EAR_THRESHOLD_PERCENTAGE = 0.8
BLINK_CONSECUTIVE_PARAMS = 3

## initialize video camera
cap = cv2.VideoCapture(0)

## loading the facial detector and face landmark(predictor that is "shape_predictor_68_face_landmarks.dat") from dlib 
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")

## Eye aspect ratio calculator

def calculate_EAR(eye_points):
    ## computing the Euclidean distances between the vertical eye landmarks
    A = distance.euclidean(eye_points[1], eye_points[5])
    B = distance.euclidean(eye_points[2], eye_points[4])
    ## computin the Euclidean distance between the horizontal eye landmarks
    C = distance.euclidean(eye_points[0], eye_points[3])

    ear = (A + B)/(2.0 * C)
    return ear

## Initialize the variables
blink_count = 0
eye_closed = False
