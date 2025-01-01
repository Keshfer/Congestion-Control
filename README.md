#  ECS 152A Programming Assignment 3 (Fall 2024)

Check the `How to use` section of the README for instructions on indicating the end of sending data.

## Congestion Control
Derived from https://github.com/Haroon96/ecs152a-fall-2023/tree/main/week7
### Docker Installation
* [Linux](https://docs.docker.com/engine/install/ubuntu/)
* [Mac](https://docs.docker.com/desktop/install/mac-install/)
* [Windows](https://docs.docker.com/desktop/install/windows-install/)

NOTE: Network profile in docker will only function properly in Linux

### How to use
(From the `docker` directory).
1. Run `./start-simulator.sh` to start running our receiver with the emulated network profile. Once it's running successfully, you will see a message saying `Receiver running`.
2. Run `python3 (Protocol file name)` to start the sender and sending of data.
3. The receiver has already been programmed to send acknowledgements to the sender similar to the receiver in the [discussion](https://github.com/Haroon96/ecs152a-fall-2023/blob/main/week7/docker/receiver.py).
4. Implement your own sender code and bind it to any port other than `5001`. Invoke your sender to send packets to `localhost`, port `5001` to communicate with the receiver.
5. Finally, on sending all the data, sender should send an empty message with the correct sequence id.
6. Receiver will then send an ack and fin message for the sender to know it's been acknowledged. (Lines 55 to 59 in receiver.py)
7. The sender should then send a message with body '==FINACK' to let the receiver know to exit (see line 31 and 32 in receiver.py)
8. Both sender and receiver will then exit.

#### Performance Metrics
Throughput: Amount of data sent per Round Trip Time (RTT)
Avg Per Packet Delay: Average time between packet received and next packet received
Average Jitter: Average variation of per packet delay from the Avg Per Packet Delay
Metric: Scoring for the protocol using the formula: (0.2 * (throughput / 2000)) + (0.1 / avg_jitter) + (0.8 / avg_perPacket_delay)

Each Protocol is tested three times and then used to find their mean and standard deviation.
