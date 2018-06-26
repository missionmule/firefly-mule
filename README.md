# firefly-mule

This application is the companion computer software designed to control the Mission Mule payload on the FireFLY6 PRO airframe.


## Communication Protocol

Communication between the Mission Mule payload and airframe is minimal.

### Upstream Communication (TX)

Upstream communication consists of a heartbeat at least once per second. The heartbeat message itself incorporates the status of the Mission Mule payload: either idle (message: `00\n`) or actively downloading from a data station (message: `01\n`).

### Downstream Communication (RX)

Downstream communication consists of the airframe autopilot sending the data station ID upon arrival. The data station ID is sent as a character string terminated with a newline (`\n`) character.


## Set up

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
