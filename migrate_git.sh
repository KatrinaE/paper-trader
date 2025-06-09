#!/bin/bash

# Create a bare clone of the local repository
mkdir -p /tmp/paper-trader-bare
pushd /tmp/paper-trader-bare
git clone --bare /Users/katrina/CascadeProjects/paper-trader .

# Copy the bare repository to the VM
multipass transfer paper-trader.git paper-trader:/home/ubuntu/

# In the VM, create a new repository and fetch the old history
multipass exec paper-trader -- bash -c '
    cd /home/ubuntu/
    git init paper-trader
    cd paper-trader
    git remote add old-repo ../paper-trader.git
    git fetch old-repo
    git reset --hard old-repo/main
'

# Clean up
popd
rm -rf /tmp/paper-trader-bare
