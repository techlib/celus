How to install Celus to Digital Ocean k8s cluster
=================================================

Inspired by https://www.digitalocean.com/community/tutorials/how-to-set-up-an-nginx-ingress-with-cert-manager-on-digitalocean-kubernetes


1. Install ingress controller
#############################

see https://kubernetes.github.io/ingress-nginx/deploy/

installation from github worked fine for me::


    kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/master/deploy/static/provider/cloud/deploy.yaml


2. Install cert-manager
#######################

see https://cert-manager.io/docs/installation/kubernetes/

installation from github worked fine for me::

    kubectl apply --validate=false -f https://github.com/jetstack/cert-manager/releases/download/v0.14.2/cert-manager.yaml


3. Bugfix
#########
Due to a bug/feature in Digital Ocean load balancer a change had to be done in order to use cert-manager
to obtain Let's Encrypt via ACME.

1) Create a `A` DNS record called e.g. `k8s-loadbalancer.celus.net` pointing to your clusters load balancer.

2) Edit ingress-nginx service::

    kubectl -n ingress-nginx edit service ingress-nginx-controller

and place `service.beta.kubernetes.io/do-loadbalancer-hostname: "k8s-loadbalancer.celus.net"` to `annotations` section.

see https://www.digitalocean.com/community/questions/how-do-i-correct-a-connection-timed-out-error-during-http-01-challenge-propagation-with-cert-manager


4. Secrets
##########

Gitlab docker repository
------------------------

see https://kubernetes.io/docs/tasks/configure-pod-container/pull-image-private-registry/

Create deploy token on www.gilab.com and initialize the `gitlab` secret using::

    kubectl create secret docker-registry gitlab --docker-server=registry.gitlab.com --docker-username=<your-name> --docker-password=<your-pword> --docker-email=<your-email>

You can try to download the secret file::

    kubectl get secret gitlab --output=yaml

And you cat try to parse the json::

    echo ... | base64 -d


Celus infrastructure
--------------------

Fill the file `secrets/secrets-celus.yaml` with appropriate values. And load it using::


    kubectl apply -f secrets/secrets-celus.yaml


5. Start Pods/Services/Ingress
##############################

Note that you can watch whether it was successfull using::
    
    kubectl get pods
    kubectl get service
    kubectl describe ingress

To remove any secret, deployment, ... you can use::

    kubectl delete -f <path>.yaml

Certificate issuer
------------------

Prepare letsencrypt issuer for `cert-manager`::

    kubectl apply -f letsencrypt-issuer.yaml


Redis
-----

Apply deployment and service::

    kubectl apply -f redis-deployment.yaml
    kubectl apply -f redis-service.yaml

Postgres (optional)
-------------------

Apply deployment and service::

    kubectl apply -f postgres-deployment.yaml
    kubectl apply -f postgres-service.yaml

Celery workers and beat
-----------------------

Apply deployment and service::

    kubectl apply -f celery-worker-deployment.yaml
    kubectl apply -f celery-beat-deployment.yaml
    kubectl apply -f celery-worker-service.yaml
    kubectl apply -f celery-beat-service.yaml

Django web
----------

Apply deployment and service::

    kubectl apply -f web-deployment.yaml
    kubectl apply -f web-service.yaml

Nginx
-----

Apply deployment, service and ingress::

    kubectl apply -f nginx-deployment.yaml
    kubectl apply -f nginx-service.yaml
    kubectl apply -f nginx-ingress.yaml
