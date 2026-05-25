"""Launch file for the side scan sonar node, using simple_launch.

Standalone usage:
    ros2 launch blueboat_control SSS_launch.py
    ros2 launch blueboat_control SSS_launch.py range_length_mm:=50000 gain_index:=4

Includable from another launch file:
    from simple_launch import SimpleLauncher
    sl = SimpleLauncher()
    sl.include('blueboat_control', 'SSS_launch.py',
               launch_arguments={'range_length_mm': 50000})
"""

from simple_launch import SimpleLauncher


def generate_launch_description():
    sl = SimpleLauncher()
    # Described here: https://docs.ceruleansonar.com/c/omniscan-450/application-programming-interface


    # ---- Network ---------------------------------------------------------
    # Defaults match the Blue Robotics Omniscan 450 SS integration guide.
    sl_port_ip            = sl.declare_arg('port_ip',            default_value='192.168.2.92')
    sl_port_tcp_port      = sl.declare_arg('port_tcp_port',      default_value=51200)
    sl_starboard_ip       = sl.declare_arg('starboard_ip',       default_value='192.168.2.93')
    sl_starboard_tcp_port = sl.declare_arg('starboard_tcp_port', default_value=51200)

    # ---- Acquisition (re-read on every ping enable) ----------------------
    sl_range_start_mm    = sl.declare_arg('range_start_mm',    default_value=0)
    sl_range_length_mm   = sl.declare_arg('range_length_mm',   default_value=30000)
    sl_msec_per_ping     = sl.declare_arg('msec_per_ping',     default_value=0)
    sl_gain_index        = sl.declare_arg('gain_index',        default_value=-1)
    sl_num_results       = sl.declare_arg('num_results',       default_value=600)
    sl_pulse_len_percent = sl.declare_arg('pulse_len_percent', default_value=0.002)

    # ---- Logging ---------------------------------------------------------
    sl_log_directory = sl.declare_arg('log_directory', default_value='data/SSS_data')

    # ---- Processor geometry ----------------------------------------------
    sl_transducer_x        = sl.declare_arg('transducer_x_m',        default_value=0.0)
    sl_transducer_y_offset = sl.declare_arg('transducer_y_offset_m', default_value=0.0)
    sl_transducer_z        = sl.declare_arg('transducer_z_m',        default_value=0.0)
    sl_base_frame_id       = sl.declare_arg('base_frame_id',         default_value='base_link')

    # ---- Processor pairing -----------------------------------------------
    sl_match_tolerance_ms  = sl.declare_arg('match_tolerance_ms', default_value=50)
    sl_pair_buffer_size    = sl.declare_arg('pair_buffer_size',   default_value=16)

    # ---- Frames ----------------------------------------------------------
    sl_port_frame_id      = sl.declare_arg('port_frame_id',      default_value='sss_port_link')
    sl_starboard_frame_id = sl.declare_arg('starboard_frame_id', default_value='sss_starboard_link')

    sl.node('blueboat_control', 'sss_node.py',
            name='side_scan_sonar',
            output='screen',
            parameters={
                'port_ip':            sl_port_ip,
                'port_tcp_port':      sl_port_tcp_port,
                'starboard_ip':       sl_starboard_ip,
                'starboard_tcp_port': sl_starboard_tcp_port,
                'range_start_mm':     sl_range_start_mm,
                'range_length_mm':    sl_range_length_mm,
                'msec_per_ping':      sl_msec_per_ping,
                'gain_index':         sl_gain_index,
                'num_results':        sl_num_results,
                'pulse_len_percent':  sl_pulse_len_percent,
                'log_directory':      sl_log_directory,
                'port_frame_id':      sl_port_frame_id,
                'starboard_frame_id': sl_starboard_frame_id,
            })

    sl.node('blueboat_control', 'sss_processor_node.py',
            name='sss_processor_node',
            output='screen',
            parameters={
                'port_topic':            '/side_scan_sonar/port/profile',
                'starboard_topic':       '/side_scan_sonar/starboard/profile',
                'match_tolerance_ms':    sl_match_tolerance_ms,
                'pair_buffer_size':      sl_pair_buffer_size,
                'transducer_x_m':        sl_transducer_x,
                'transducer_y_offset_m': sl_transducer_y_offset,
                'transducer_z_m':        sl_transducer_z,
                'base_frame_id':         sl_base_frame_id,
                'log_directory':         sl_log_directory,
            })

    return sl.launch_description()
