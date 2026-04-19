#!/bin/bash

Action="$1"
Arg1="$2"
Arg2="$3"
Arg3="$4"

case "$Action" in

    SafetyCheck)
        if pgrep -x "NullWire" > /dev/null; then
            echo "yes"
        else
            echo "no"
        fi
    ;;


    #-------------------------------------- Sinks
    CreateSink)
        pactl load-module module-null-sink sink_name="$Arg1" \
          sink_properties=device.description="$Arg1"
        exit 0
    ;;

    DeleteSink)
        ModuleId=$(pactl list short modules | grep "sink_name=$Arg1" | awk '{print $1}')

        if [[ -n "$ModuleId" ]]; then
            echo "Deleting sink: $Arg1"
            pactl unload-module "$ModuleId"
        fi

        exit 0
    ;;

    ClearSinks)
        pactl unload-module module-null-sink 2>/dev/null || \
        pactl list short modules | grep module-null-sink | awk '{print $1}' | while read -r Id; do
            pactl unload-module "$Id"
        done

        exit 0
    ;;

    #------------------------------------------ Aux
    ConnectSinkToAux)
        Sink="$Arg1"
        Device="$Arg2"
        Mono="$Arg3"

        if [[ "$Mono" == "1" ]]; then
            pw-link "$Sink:monitor_FL" "$Device:playback_FL" 2>/dev/null || true
            pw-link "$Sink:monitor_FL" "$Device:playback_FR" 2>/dev/null || true
            pw-link "$Sink:monitor_FR" "$Device:playback_FL" 2>/dev/null || true
            pw-link "$Sink:monitor_FR" "$Device:playback_FR" 2>/dev/null || true
        else
            pw-link "$Sink:monitor_FL" "$Device:playback_FL" 2>/dev/null || true
            pw-link "$Sink:monitor_FR" "$Device:playback_FR" 2>/dev/null || true
        fi 

        exit 0
    ;;

    RemoveSinkFromAux)
        Sink="$Arg1"
        Device="$Arg2"

        echo "Disconnect $Sink → $Device"
        pw-link -d "$Sink:monitor_FL" "$Device:playback_FL" 2>/dev/null
        pw-link -d "$Sink:monitor_FR" "$Device:playback_FR" 2>/dev/null
        pw-link -d "$Sink:monitor_FL" "$Device:playback_FR" 2>/dev/null
        pw-link -d "$Sink:monitor_FR" "$Device:playback_FL" 2>/dev/null

        exit 0
    ;;

    DisconnectAllSinkToAux)
        Sink="$Arg1"

        pw-link -l | grep "$Sink:monitor" | while read -r line; do
            Source=$(echo "$line" | awk '{print $1}')
            Target=$(echo "$line" | awk '{print $3}')
            pw-link -d "$Source" "$Target" 2>/dev/null
        done
        exit 0
    ;;

    #------------------------------------------ Mic

    ConnectMicToSink)
        Mic="$Arg1"
        Sink="$Arg2"
        Ports=$(pw-link -o | awk -v mic="$Mic" '$1 ~ "^"mic":" {print $1}')
        Success=1
        for Port in $Ports; do
            case "$Port" in
                *capture_MONO)
                    pw-link "$Port" "$Sink:playback_FL" || Success=0 
                    pw-link "$Port" "$Sink:playback_FR" || Success=0
                ;;
                *capture_FL)
                    pw-link "$Port" "$Sink:playback_FL" || Success=0
                ;;
                *capture_FR)
                    pw-link "$Port" "$Sink:playback_FR" || Success=0
                ;;
            esac
        done

        exit $((1 - Success))
    ;;

    RemoveMicFromSink)
        Mic="$Arg1"
        Sink="$Arg2"

        echo "Disconnect $Mic → $Sink"

        Ports=$(pw-link -o | awk -v mic="$Mic" '$1 ~ "^"mic":" {print $1}')

        for Port in $Ports; do
            pw-link -d "$Port" "$Sink:playback_FL" 2>/dev/null || true
            pw-link -d "$Port" "$Sink:playback_FR" 2>/dev/null || true
        done

        exit 0
    ;;

    RemoveMicFromAllSinks)
        Mic="$Arg1"

        echo "Disconnect $Mic from ALL sinks"

        pw-link -l | grep "$Mic:capture" | while read -r line; do
            Source=$(echo "$line" | awk '{print $1}')
            Target=$(echo "$line" | awk '{print $3}')

            pw-link -d "$Source" "$Target" 2>/dev/null
        done

        exit 0
    ;;
    

    
    #---------------------------------------------Sources
    ConnectSourceToSink)
        InputName="$Arg1"
        TargetSink="$Arg2"

        echo "Attach $InputName → $TargetSink"

        pactl list sink-inputs | while read -r line; do

            if [[ "$line" == *"Sink Input #"* ]]; then
                Id=$(echo "$line" | awk '{print $3}' | tr -d '#')
            fi

            if [[ "$line" == *"application.name"* && "$line" == *"$InputName"* ]]; then
                echo "Moving input $Id → $TargetSink"
                pactl move-sink-input "$Id" "$TargetSink"
            fi

        done

        exit 0
    ;;

    RemoveSourceFromSink)
        InputName="$Arg1"

        echo "Detach $InputName → default"

        DefaultSink=$(pactl get-default-sink)

        pactl list sink-inputs | while read -r line; do

            if [[ "$line" == *"Sink Input #"* ]]; then
                Id=$(echo "$line" | awk '{print $3}' | tr -d '#')
            fi

            if [[ "$line" == *"application.name"* && "$line" == *"$InputName"* ]]; then
                echo "Moving input $Id → $DefaultSink"
                pactl move-sink-input "$Id" "$DefaultSink"
            fi

        done

        exit 0
    ;;

    

    

esac