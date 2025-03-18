from app import config
import requests
import cv2
import numpy as np
import urllib
import time
import json
from app.detector import gesturemodelfunctions
import gc
import contextlib
import os
import copy
import uuid

def pubinitial(cameraname):
    """Publish an initial state for a camera with empty person and gesture"""
    topic = config.config['gesture']['topic'] + "/" + cameraname
    payload = {
        'id': '',
        'person': '', 
        'gesture': '',
        'timestamp': int(time.time()),
        'camera': cameraname,
        'duration': 0,
        'double_take': {
            'used': False,
            'results': {}
        },
        'hand_detection': {}
    }
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Publishing initial state for: {cameraname}")
    ret = config.client.publish(topic, json.dumps(payload), retain=True)
    config.sentpayload[cameraname] = payload

def pubresults(cameraname, name, gesture, process_duration=0, dt_results=None, hand_rect=None, process_id=None):
    """Publish detection results for a camera with enhanced data"""
    topic = config.config['gesture']['topic'] + "/" + cameraname
    
    # Generate unique ID if not provided
    if not process_id:
        process_id = str(int(time.time() * 1000))  # Milliseconds timestamp as ID
        
    payload = {
        'id': process_id,
        'person': name,
        'gesture': gesture,
        'timestamp': int(time.time()),
        'camera': cameraname,
        'duration': round(process_duration, 3),
        'double_take': {
            'used': 'double-take' in config.config and config.should_use_double_take(cameraname),
            'results': dt_results or {}
        },
        'hand_detection': hand_rect or {}
    }
    
    if config.sentpayload[cameraname] != payload:
        if name or gesture:  # Chỉ in log khi có dữ liệu thực
	        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Publishing to {topic}: {str(payload)}")
        ret = config.client.publish(topic, json.dumps(payload), retain=True)
        config.sentpayload[cameraname] = payload

def getmatches(cameraname):
    """Get face recognition matches from Double-Take"""
    if 'double-take' not in config.config:
        return None
        
    url = f"http://{config.config['double-take']['host']}:{config.config['double-take']['port']}/api/recognize"
    url += f"?url=http://{config.config['frigate']['host']}:{config.config['frigate']['port']}/api/{cameraname}/latest.jpg"
    url += f"&attempts=1&camera={cameraname}"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error getting matches from Double-Take: {response.status_code}")
            return None
    except Exception as e:
        print(f"Exception while getting matches from Double-Take: {str(e)}")
        return None

def getlatestimg(cameraname):
    """Get the latest image from Frigate"""
    url = f"http://{config.config['frigate']['host']}:{config.config['frigate']['port']}/api/{cameraname}/latest.jpg"
    try:
        with contextlib.closing(urllib.request.urlopen(url)) as req:
            arr = np.asarray(bytearray(req.read()), dtype=np.uint8)
        img = cv2.imdecode(arr, -1)
        return img
    except Exception as e:
        print(f"Exception while getting latest image from Frigate: {str(e)}")
        return None

def should_process_result(matches):
    """Determine if we should process this result based on Double-Take matches"""
    if not matches or 'results' not in matches:
        return False
    
    for result in matches.get('results', []):
        if result.get('match_found', False):
            return True
    
    return False

def get_person_to_process(matches):
    """Get the person name and confidence from Double-Take matches"""
    if not matches or 'results' not in matches:
        return None, 0
        
    best_match = None
    best_confidence = 0
    
    for result in matches.get('results', []):
        if result.get('match_found', False):
            confidence = result.get('match_confidence', 0)
            if confidence > best_confidence:
                best_confidence = confidence
                best_match = result.get('match_name')
            
    # Check if person is in allowed list
    if best_match and not config.is_person_allowed(best_match):
        return None, 0
        
    return best_match, best_confidence

def save_annotated_image(image, cameraname, gesture, hand_rect, process_id, landmark_points=None, dt_results=None):
    """Save annotated image with hand landmarks, bounding box, and gesture label"""
    if not config.config['storage']['enabled'] or not config.config['storage'].get('save_annotated', True):
        return
        
    # Create storage directory if it doesn't exist
    storage_path = config.config['storage']['path']
    os.makedirs(storage_path, exist_ok=True)
    
    # Draw bounding box and gesture text on the image
    annotated_img = copy.deepcopy(image)
    
    # Draw hand bounding box and gesture text
    if hand_rect:
        cv2.rectangle(annotated_img, 
                     (hand_rect['x'], hand_rect['y']), 
                     (hand_rect['x'] + hand_rect['width'], hand_rect['y'] + hand_rect['height']), 
                     (0, 255, 0), 2)
        
        # Add gesture text
        if gesture:
            cv2.putText(annotated_img, gesture, 
                       (hand_rect['x'], hand_rect['y'] - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
    
    # Draw hand landmarks if available
    if landmark_points:
        # Connect landmarks with lines to form a hand skeleton
        connections = [
            (0, 1), (1, 2), (2, 3), (3, 4),  # Thumb
            (0, 5), (5, 6), (6, 7), (7, 8),  # Index finger
            (0, 9), (9, 10), (10, 11), (11, 12),  # Middle finger
            (0, 13), (13, 14), (14, 15), (15, 16),  # Ring finger
            (0, 17), (17, 18), (18, 19), (19, 20),  # Pinky
            (5, 9), (9, 13), (13, 17)  # Palm connections
        ]
        
        # Draw connections
        for connection in connections:
            if len(landmark_points) > max(connection):
                start_point = tuple(landmark_points[connection[0]])
                end_point = tuple(landmark_points[connection[1]])
                cv2.line(annotated_img, start_point, end_point, (255, 0, 0), 2)
        
        # Draw points
        for point in landmark_points:
            cv2.circle(annotated_img, tuple(point), 5, (0, 0, 255), -1)
    
    # Draw face detection box and person name if available from Double-Take
    if dt_results and 'results' in dt_results:
        for result in dt_results.get('results', []):
            if result.get('match_found', False) and 'face_bbox' in result:
                # Extract face bounding box coordinates
                bbox = result.get('face_bbox', [0, 0, 0, 0])
                x, y, w, h = int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3])
                
                # Draw face bounding box
                cv2.rectangle(annotated_img, (x, y), (x + w, y + h), (255, 255, 0), 2)
                
                # Add person name
                person_name = result.get('match_name', 'unknown')
                confidence = result.get('match_confidence', 0)
                label = f"{person_name} ({confidence:.2f})"
                cv2.putText(annotated_img, label, (x, y - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
    
    # Add timestamp
    timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S")
    cv2.putText(annotated_img, f"Time: {timestamp_str}", 
               (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # Save image with timestamp and process ID
    timestamp = int(time.time())
    filename = f"{storage_path}/{cameraname}_{timestamp}_{process_id}.jpg"
    cv2.imwrite(filename, annotated_img)
    
    # Also save the JSON results for this image
    json_filename = f"{storage_path}/{cameraname}_{timestamp}_{process_id}.json"
    result_data = {
        'id': process_id,
        'camera': cameraname,
        'timestamp': timestamp,
        'gesture': gesture,
        'hand_rect': hand_rect,
        'double_take': dt_results
    }
    with open(json_filename, 'w') as f:
        json.dump(result_data, f, indent=2)
    
    # Run cleanup to remove old images based on retention policy
    config.cleanup_old_images()

def lookforhands():
    """Main function to detect hands and gestures"""
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Publishing availability")
    topic = config.config['gesture']['topic'] + "/" + 'availability'
    payload = "online"
    config.client.publish(topic, payload, retain=True)
    
    for camera in config.config['frigate']['cameras']:
        pubinitial(camera)
    
    while True:
        for cameraname in config.numpersons:
            numcamerapeople = config.numpersons[cameraname]
            if numcamerapeople > 0:
                process_start_time = time.time()
                try:
                    # Generate a unique process ID for this detection cycle
                    process_id = str(int(time.time() * 1000))
                    
                    use_double_take = config.should_use_double_take(cameraname)
                    detect_all_results = config.config.get('double-take', {}).get('detect_all_results', False)
                    
                    person_name = None
                    dt_results = None
                    
                    if use_double_take:
                        dt_start_time = time.time()
                        matches = getmatches(cameraname)
                        dt_time = time.time() - dt_start_time
                        dt_results = matches  # Store the full results for MQTT payload
                        
                        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Camera {cameraname}: Double-Take processed in {dt_time:.3f}s")
                        
                        if detect_all_results or should_process_result(matches):
                            person_name, person_confidence = get_person_to_process(matches)
                            if not detect_all_results and not person_name:
                                print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Camera {cameraname}: No match found, skipping gesture detection")
                                pubresults(cameraname, '', '', process_duration=0, dt_results=dt_results, process_id=process_id)
                                continue
                        else:
                            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Camera {cameraname}: No match and detect_all_results is False, skipping")
                            pubresults(cameraname, '', '', process_duration=0, dt_results=dt_results, process_id=process_id)
                            continue
                    
                    img = getlatestimg(cameraname)
                    if img is not None:
                        gesture, hand_rect, landmark_points = gesturemodelfunctions.gesturemodelmatch(img)  # Update this line
                        
                        # Calculate total processing time
                        process_duration = time.time() - process_start_time
                        
                        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Camera {cameraname}: Gesture analysis result: '{gesture}'")
                        
                        # Save annotated image if storage is enabled
                        if gesture and hand_rect:
                            save_annotated_image(img, cameraname, gesture, hand_rect, process_id, landmark_points, dt_results)
                        
                        # Publish results with all the new information
                        pubresults(
                            cameraname=cameraname,
                            name=person_name or 'unknown',
                            gesture=gesture,
                            process_duration=process_duration,
                            dt_results=dt_results,
                            hand_rect=hand_rect,
                            process_id=process_id
                        )
                    else:
                        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Camera {cameraname}: Failed to get image")
                        pubresults(cameraname, '', '', process_id=process_id)
                    
                    total_process_time = time.time() - process_start_time
                    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Camera {cameraname}: Total processing time: {total_process_time:.3f}s")
                except Exception as e:
                    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Error processing camera {cameraname}: {str(e)}")
            else:
                pubresults(cameraname, '', '')
                continue
        
        gc.collect()
        time.sleep(0.5)
