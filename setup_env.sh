#!/bin/bash
# SySL Environment Setup Script
# This script sets up the PYTHONPATH with all required dependencies

echo "🔧 Setting up SySL development environment..."

# Export PYTHONPATH with all required dependencies
export PYTHONPATH="$PYTHONPATH:/sensei-fs-3/users/aganeshan/projects/mpspy/data_munch:/home/colligo/projects/coref:/home/colligo/projects/mpspy/mpspy:/home/colligo/projects/vsic_mps:/sensei-fs-3/users/aganeshan/projects/geolipi:/home/colligo/projects/mpspy/sysl"

echo "✅ PYTHONPATH configured with dependencies:"
echo "   - data_munch: /sensei-fs-3/users/aganeshan/projects/mpspy/data_munch"
echo "   - coref: /home/colligo/projects/coref"
echo "   - mpspy: /home/colligo/projects/mpspy/mpspy"
echo "   - vsic_mps: /home/colligo/projects/vsic_mps"
echo "   - geolipi: /sensei-fs-3/users/aganeshan/projects/geolipi"
echo "   - sysl: /home/colligo/projects/mpspy/sysl"
echo ""
echo "🚀 Environment ready! You can now:"
echo "   - Import SySL modules: import sysl.symbolic as sls"
echo "   - Run SySL scripts and examples"
echo "   - Use the shader generation pipeline"
echo ""
echo "💡 To make this permanent, add this script to your ~/.bashrc:"
echo "   echo 'source /sensei-fs-3/users/aganeshan/projects/mpspy/sysl/setup_env.sh' >> ~/.bashrc"

