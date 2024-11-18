from flask import jsonify, request,app
from .models import Program
from sqlalchemy import or_

@app.route('/search')
def search():
    query = request.args.get('query', '')
    if not query:
        return jsonify({'programs': []})
    
    search_results = Program.query.filter(
        or_(
            Program.Program_name.ilike(f'%{query}%'),
            Program.Program_description.ilike(f'%{query}%'),
            Program.university.ilike(f'%{query}%'),
            Program.career_prospects.ilike(f'%{query}%')
        )
    ).all()
    
    return jsonify({
        'programs': [program.to_dict() for program in search_results]
    }) 