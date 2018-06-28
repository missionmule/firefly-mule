# firefly-mule

This application is the companion computer software designed to control the Mission Mule payload on the FireFLY6 PRO airframe.


## Communication Protocol

Communication between the Mission Mule payload and airframe is minimal.

### TX Communication

TX communication consists of a heartbeat at least once per second. The heartbeat message itself incorporates the status of the Mission Mule payload: either idle (message: `\x00`) or actively downloading from a data station (message: `\x01`).

### RX Communication

RX communication consists of the airframe autopilot sending the data station ID upon arrival. The data station ID is sent as a character string terminated with a newline (`\n`) character.


## Set Up

To set up and run the application, execute:

```
make init
make run
```

## Testing

To test the application, execute:

```
make test
```
