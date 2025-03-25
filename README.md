# BGA-discord-bot
Discord bot for Board Game Arena notifications

Will monitor available boards for users that opt in and notify them when it is their turn to play.

## setup
setup .env or env vars:
```
DISCORD_TOKEN=MIi...
NOTIFY_CHANNEL_ID=3u98sjfd9in....
```

create a python venv and activate it. Install requirements and run script

```
pip install --no-cache-dir -r requirements.txt
python script.py
```

### docker (build, run, push)

Enable [Enable containerd image store on Docker Engine](https://docs.docker.com/storage/containerd/#enable-containerd-image-store-on-docker-engine)

```
docker buildx bake -f docker-bake.dev.hcl
docker run -e DISCORD_TOKEN="somevalue" -e NOTIFY_CHANNEL_ID="somevalue" -it docker.io/johrad/bga-discord-bot
docker push docker.io/johrad/bga-discord-bot
```

### kubernetes
```
# in k8s-manifests.yaml:
# modify:
---
apiVersion: v1
kind: Secret
metadata:
  name: bga-env-var-secrets
  namespace: bga-discord-bot
type: Opaque
data:
  discord_token: <base64 encoded token>          # <-- modify this
  notify_channel_id: <base64 encoded channelid>  # <-- modify this
---
# probably, also want to set PV hostPath differently:
---
apiVersion: v1
kind: PersistentVolume
metadata:
  name: bga-discord-bot-pv
  namespace: bga-discord-bot
spec:
  capacity:
    storage: 1Gi
  accessModes:
    - ReadWriteOnce
  hostPath:
    path: /mnt/path  # <-- modify this
  persistentVolumeReclaimPolicy: Retain
  storageClassName: bga-discord-botfs
---
# then execute:
kubectl apply -f k8s-manifests.yaml
```

## Command Setup
After adding the bot, server administrators need to:
1. Go to Server Settings -> Integrations
2. Find the bot and click "Manage"
3. Under "Command Permissions":
   - Set the channel restrictions for host commands to only allow them in your designated hosting channel
   - Optionally adjust role permissions if you want non-admin users to use the commands
