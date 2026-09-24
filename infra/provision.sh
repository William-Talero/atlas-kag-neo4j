#!/usr/bin/env bash
# Aprovisiona ATLAS KAG sobre Neo4j en Azure Container Instances.
#
# La contraseña se genera aquí, se escribe en .env (modo 600) y se envía al
# contenedor como variable segura: no aparece en `az container show` ni se
# imprime en ningún momento.
#
#   ./infra/provision.sh [region]
#
set -euo pipefail

RG="${RG:-rg-atlas-kag-neo4j}"
LOC="${1:-${LOC:-centralus}}"
IMAGEN="${IMAGEN:-neo4j:5-community}"
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

paso() { printf '\n\033[1m· %s\033[0m\n' "$*"; }

paso "Comprobando sesión de Azure"
az account show -o none || { echo "Ejecuta 'az login' primero." >&2; exit 1; }

paso "Registrando el proveedor Microsoft.ContainerInstance"
estado=$(az provider show -n Microsoft.ContainerInstance --query registrationState -o tsv 2>/dev/null || echo NotRegistered)
if [[ "$estado" != "Registered" ]]; then
  az provider register --namespace Microsoft.ContainerInstance
  until [[ "$(az provider show -n Microsoft.ContainerInstance --query registrationState -o tsv)" == "Registered" ]]; do
    sleep 10
  done
fi
echo "  proveedor registrado"

SUF="$(openssl rand -hex 3)"
ACI="${ACI:-aci-atlas-neo4j-$SUF}"
DNS="${DNS:-atlas-neo4j-$SUF}"

paso "Creando el grupo de recursos $RG"
az group create -n "$RG" -l "$LOC" \
  --tags proyecto=atlas-kag modelo=KAG motor=neo4j -o none

paso "Generando credenciales y escribiendo .env"
NEOPASS="$(openssl rand -hex 16)"
umask 077
cat > "$RAIZ/.env" <<ENV
# Generado por infra/provision.sh el $(date -u +%Y-%m-%dT%H:%M:%SZ)
NEO4J_URI=bolt://$DNS.$LOC.azurecontainer.io:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=$NEOPASS
NEO4J_DB=neo4j
EMBED_DIM=256
DEMO_MODE=live
ENV

paso "Creando el contenedor $ACI ($IMAGEN)"
# Sin volumen persistente: esta suscripción tiene una política que impide la
# autenticación por clave compartida en Storage, y ACI solo monta Azure Files
# con clave. El grafo se reconstruye con `make reload`, que tarda ~45 s.
az container create -g "$RG" -n "$ACI" \
  --image "$IMAGEN" \
  --os-type Linux --cpu 2 --memory 4 \
  --ports 7474 7687 --protocol TCP \
  --ip-address Public --dns-name-label "$DNS" \
  --secure-environment-variables NEO4J_AUTH="neo4j/$NEOPASS" \
  --environment-variables \
     NEO4J_server_default__listen__address=0.0.0.0 \
     NEO4J_server_bolt_advertised__address="$DNS.$LOC.azurecontainer.io:7687" \
     NEO4J_server_http_advertised__address="$DNS.$LOC.azurecontainer.io:7474" \
     NEO4J_server_memory_heap_max__size=2G \
     NEO4J_server_memory_pagecache_size=512m \
  --restart-policy OnFailure \
  -o none

printf 'RG=%s\nLOC=%s\nACI=%s\nDNS=%s\n' "$RG" "$LOC" "$ACI" "$DNS" \
  > "$RAIZ/infra/.provision-env"

cat <<FIN

Listo.

  bolt       bolt://$DNS.$LOC.azurecontainer.io:7687
  navegador  http://$DNS.$LOC.azurecontainer.io:7474
  usuario    neo4j (la contraseña quedó en .env, modo 600)

El puerto bolt está abierto a internet: es un entorno de demostración. Para algo
real, ponlo detrás de una red virtual o usa Neo4j AuraDB.

Siguiente:

  make install
  make reload
  make verify

FIN
