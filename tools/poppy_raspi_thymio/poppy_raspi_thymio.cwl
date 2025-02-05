class: CommandLineTool
cwlVersion: v1.0
doc: "Raspberry Pi—Thymio Vision"
hints:
  - class: DockerRequirement
    dockerPull: quay.io/biocontainers/python:3.12

inputs:
  help:
    type: boolean
    doc: |
      Request help
    default: False
    inputBinding:
      prefix: "--help"
  
outputs:
  stdout:
    type: stdout

baseCommand:
  - "poppy_raspi_thymio"
