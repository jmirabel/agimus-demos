#!/usr/bin/python2

# TODO in simulation
# unpause gazebo physics

# Demo steps
# 1.a compute initial clusters to cover the part (HPP)
# 1.b localize the robot mobile base             (PAL)
# for each remaining clusters from 1.a:
#    2. move mobile base to cluster position (HPP -> Agimus (PAL))
#    3. localize the part and recompute trajectory to cover the cluster (Agimus -> HPP)
#       eventually, modify the cluster to reflect the new base position.
#    4.a execute arm motion (HPP -> Agimus (sot))
#    4.b eventually, recompute new remaining clusters.
ros_initialized = False
def init_ros_node():
    import rospy
    global ros_initialized
    if not ros_initialized:
        rospy.init_node("hpp")
    ros_initialized = True

def get_current_config(robot, q0):
    init_ros_node()

    from rospy import wait_for_message
    from geometry_msgs.msg import PoseWithCovarianceStamped
    from sensor_msgs.msg import JointState

    # Build initial position
    msg = wait_for_message("/amcl_pose", PoseWithCovarianceStamped)
    P = msg.pose.pose.position
    Q = msg.pose.pose.orientation
    # conversion from
    # cos(t) = 2 cos(t/2)**2 - 1
    # sin(t) = 2 cos(t/2) sin(t/2)
    q0[0:4] = P.x, P.y, 2 * Q.w**2 - 1, 2 * Q.w * Q.z
    # Acquire robot state
    msg = wait_for_message("/joint_states", JointState)
    for ni, qi in zip(msg.name, msg.position):
        jni = "tiago/"+ni
        if robot.getJointConfigSize(jni) != 1:
            continue
        try:
            rk = robot.rankInConfiguration[jni]
        except KeyError:
            continue
        assert robot.getJointConfigSize(jni) == 1
        q0[rk] = qi
    return q0

def get_cylinder_pose(robot, q0, timeout=5.):
    # the cylinder should be placed wrt to the robot, as this is what the sensor tells us.
    # Get pose of object wrt to the camera using TF
    import tf2_ros, rospy, geometry_msgs.msg
    init_ros_node()

    tfBuffer = tf2_ros.Buffer()
    listener = tf2_ros.TransformListener(tfBuffer)

    camera_frame = 'xtion_optical_frame'
    object_frame = 'part/base_link_measured'

    from pinocchio import XYZQUATToSE3, SE3ToXYZQUAT
    wMc = XYZQUATToSE3(robot.hppcorba.robot.getJointsPosition(q0, ["tiago/"+camera_frame])[0])

    try:
        _cMo = tfBuffer.lookup_transform(camera_frame, object_frame,
                rospy.Time(), rospy.Duration(timeout))
        _cMo = _cMo.transform
    except (tf2_ros.LookupException, tf2_ros.ConnectivityException, tf2_ros.ExtrapolationException) as e:
        print('could not get TF transform : ', e)
        return
    cMo = XYZQUATToSE3([ _cMo.translation.x, _cMo.translation.y, _cMo.translation.z,
            _cMo.rotation.x, _cMo.rotation.y, _cMo.rotation.z, _cMo.rotation.w ])
    rk = robot.rankInConfiguration['part/root_joint']
    assert robot.getJointConfigSize('part/root_joint') == 7
    qres = q0[:]
    qres[rk:rk+7] = SE3ToXYZQUAT (wMc * cMo)
    return qres

def get_current_robot_and_cylinder_config(robot, q0, timeout=5.):
    qrob = get_current_config(robot, q0)
    return get_cylinder_pose(robot, qrob, timeout=timeout)
