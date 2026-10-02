#!/bin/bash
# ===========================================================================
# Copy script for Writingway to get all Projects and settings files from a 
# previous vesion (macOS)
# Usage: "source ./copy_userFiles.sh ../Writingway-old/"
#    Copy from within the new Writingway directory, and specify the
#    path to the old Writingwaydirectory using a trailing slash.
# ==========================================================================

# Check if the source directory is provided
if [ -z "$1" ]; then
  echo "Usage: $0 source_directory"
  exit 1
fi

SOURCE_DIR=$1

# Copy specific files and directories to the source directory
echo "Copying project_settings.json"
cp "$SOURCE_DIR"project_settings.json ./
echo "Copying projects.json"
cp "$SOURCE_DIR"projects.json ./
echo "Copying settings.json"
cp "$SOURCE_DIR"settings.json ./
echo "Copying prompts.bak.json"
cp "$SOURCE_DIR"prompts.bak.json ./
echo "Copying prompts.json"
cp "$SOURCE_DIR"prompts.json  ./
echo "Copying conversations.json"
cp "$SOURCE_DIR"conversations.json ./
echo "Copying Projects directory"
cp -r "$SOURCE_DIR"Projects ./Projects
echo "assets directory"
cp -r "$SOURCE_DIR"assets ./

# Find all project structure files (e.g., MyFirstProject_structure.json)
PROJECT_FILES=$(ls "$SOURCE_DIR" | grep "_structure.json")

# Loop through each project structure file and copy it
for FILE in $PROJECT_FILES; do
  echo "Copying $FILE"
  cp "$SOURCE_DIR""$FILE" ./
done

echo "All user files from "$SOURCE_DIR" have been copied."