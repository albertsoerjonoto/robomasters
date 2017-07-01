#!/usr/bin/env python

## PID control for yaw and pitch of turret towards target from target input from webcam
## Subsribe to /roi topic to obtain position data
## Publish angular velocity of turret to arduino through /vel_cmd topic

import rospy
import numpy as np
from time import time
from sensor_msgs.msg import Joy
from sensor_msgs.msg import RegionOfInterest

state_x = 0
state_y = 0
stash = []
updatetime = time()

def callback(roi):
    global updatetime
    updatetime = time()

    # print "/roi = ", roi.x_offset, roi.y_offset

    #calculate center of roi
    center = [0, 0]
    center[0] = (roi.x_offset + roi.width/2) /10
    center[1] = (roi.y_offset + roi.height/2) /10

    if len(stash)==10:
            del stash[0]
    stash.append(center)

    heatmap = np.zeros((102,58), dtype=np.uint8)
    for ctr in stash:
        heatmap[ctr[0], ctr[1]] += 1
    
    global state_x, state_y
    state_x, state_y = np.unravel_index(heatmap.argmax(), heatmap.shape) #only first occurrence returned

def turret():
    global state_x, state_y, updatetime
    pub = rospy.Publisher('/vel_cmd', Joy, queue_size=10)
    rospy.init_node('turret', anonymous=True)
    rospy.Subscriber('/roi', RegionOfInterest, callback)
    rate = rospy.Rate(10) # 10Hz

    # PID parameters
    xMax = 102
    yMax = 57
    outMin = 524
    outNeutral = 1024
    outMax = 1524

    # needs tuning again
    Kp = 1.2
    Ki = 0.01
    Kd = 0.9

    target_x = xMax/2
    target_y = yMax/2
    
    errorp_x = 0
    errorp_y = 0

    while not rospy.is_shutdown():
        if time() - updatetime < 3:
            error_x = target_x - state_x
            output_x = Kp*error_x + Ki*(error_x+errorp_x) + Kd*(error_x-errorp_x)
            output_x = outNeutral - output_x
        
            error_y = state_y - target_y
            output_y = Kp*error_y + Ki*(error_y+errorp_y) + Kd*(error_y-errorp_y)
            output_y = outNeutral - output_y
        
            errorp_x = error_x
            errorp_y = error_y

            print "state = ", state_x, state_y
            print "target = ", target_x, target_y
            print "error = ", error_x, error_y

            if abs(error_x) < xMax/10 and abs(error_y) < yMax/6:
                shoot = 1
            else:
                shoot =0

        else:
            state_x = 0
            state_y = 0
            output_x = outNeutral
            output_y = outNeutral
            shoot = 0
            
        output = Joy()
        output.buttons = [outNeutral, outNeutral, output_x, output_y, shoot]

        # rospy.loginfo("x_pos = %d", state_x)
        # rospy.loginfo("y_pos = %d", state_y)
        # rospy.loginfo("yaw = %d", output.buttons[2])
        # rospy.loginfo("pitch = %d", output.buttons[3])
        # rospy.loginfo("shoot = %d", output.buttons[4])

        pub.publish(output)
        rate.sleep()

if __name__ == '__main__':
    try:
        turret()
    except rospy.ROSInterruptException:
        pass