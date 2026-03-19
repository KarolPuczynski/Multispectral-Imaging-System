;docs for grbl commands
;https://www.sainsmart.com/blogs/news/grbl-v1-1-quick-reference?srsltid=AfmBOooLKuBRPyPlQbkW4n3DT5nuxABBULs-m1P1F4lWH_mXtHo27Lxf
;
$0=10      ; Step pulse, microseconds
$1=25      ; Step idle delay, milliseconds
$2=0       ; Step port invert, XYZmask
$3=4       ; Direction port invert, XYZmask
$4=0       ; Step enable invert, (0=Disable, 1=Invert)
$5=0       ; Limit pins invert, (0=N-Open. 1=N-Close)
$6=0       ; Probe pin invert, (0=N-Open. 1=N-Close)
$10=1      ; Status report, mask
$11=0.010   ; Junction deviation, mm
$12=0.002   ; Arc tolerance, mm
$13=0      ; Report in inches, (0=mm. 1=Inches)
$20=0      ; Soft limits, (0=Disable. 1=Enable)
$21=1      ; Hard limits, (0=Disable. 1=Enable)
$22=1      ; Homing cycle, (0=Disable. 1=Enable)
$23=7      ; Homing direction invert, XYZmask
$24=20.000  ; Homing feed, mm/min
$25=100.000  ; Homing seek, mm/min
$26=250     ; Homing debounce, milliseconds
$27=2.000   ; Homing pull-off, mm
$30=1000    ; Max spindle speed, RPM
$31=0      ; Min spindle speed, RPM
$32=0      ; Laser mode, (0=Off, 1=On)
$100=1600.000; X steps/mm
$101=1600.000; Y steps/mm
$102=40.000; Z steps/mm
$110=500.000; X Max rate, mm/min
$111=500.000; Y Max rate, mm/min
$112=500.000; Z Max rate, mm/min
$120=10.000 ; X Acceleration, mm/sec^2
$121=10.000 ; Y Acceleration, mm/sec^2
$122=10.000 ; Z Acceleration, mm/sec^2
$130=200.000; X Max travel, mm
$131=200.000; Y Max travel, mm
$132=200.000; Z Max travel, mm