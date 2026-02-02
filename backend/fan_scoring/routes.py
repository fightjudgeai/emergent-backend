"""
Fan Scoring API Routes
Enables fans to score fights via QR code access
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timezone
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/fan", tags=["Fan Scoring"])

# Database reference - will be set during initialization
db = None

def init_fan_routes(database):
    global db
    db = database
    logger.info("✅ Fan Scoring routes initialized")


# ============== Models ==============

class FanRegistration(BaseModel):
    username: str
    email: Optional[str] = None


class FanScoreSubmission(BaseModel):
    bout_id: str
    round_number: int
    red_score: int  # 7-10
    blue_score: int  # 7-10
    fan_id: Optional[str] = None  # Guest if not provided
    session_id: Optional[str] = None


class SimpleScoreSubmission(BaseModel):
    bout_id: str
    round_number: int
    winner: str  # RED, BLUE, or DRAW
    fan_id: Optional[str] = None
    session_id: Optional[str] = None


# ============== Fan Authentication ==============

@router.post("/register")
async def register_fan(data: FanRegistration):
    """Register a new fan account for leaderboard tracking"""
    try:
        # Check if username exists
        existing = await db.fan_users.find_one({"username": data.username.lower()})
        if existing:
            raise HTTPException(status_code=400, detail="Username already taken")
        
        fan_id = str(uuid.uuid4())[:8]
        fan_doc = {
            "fan_id": fan_id,
            "username": data.username.lower(),
            "display_name": data.username,
            "email": data.email,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "total_score": 0,
            "rounds_scored": 0,
            "correct_predictions": 0,
            "events_attended": []
        }
        
        await db.fan_users.insert_one(fan_doc)
        
        return {
            "success": True,
            "fan_id": fan_id,
            "username": data.username,
            "message": "Account created! You can now track your scores on the leaderboard."
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering fan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/guest-session")
async def create_guest_session():
    """Create a guest session for anonymous scoring"""
    try:
        session_id = str(uuid.uuid4())[:12]
        session_doc = {
            "session_id": session_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "scores": [],
            "is_guest": True
        }
        
        await db.fan_sessions.insert_one(session_doc)
        
        return {
            "success": True,
            "session_id": session_id,
            "message": "Guest session created. Sign up to save your scores to the leaderboard!"
        }
    except Exception as e:
        logger.error(f"Error creating guest session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profile/{fan_id}")
async def get_fan_profile(fan_id: str):
    """Get fan profile and stats"""
    try:
        fan = await db.fan_users.find_one({"fan_id": fan_id}, {"_id": 0})
        if not fan:
            raise HTTPException(status_code=404, detail="Fan not found")
        
        # Calculate accuracy
        if fan.get("rounds_scored", 0) > 0:
            accuracy = (fan.get("correct_predictions", 0) / fan["rounds_scored"]) * 100
        else:
            accuracy = 0
        
        fan["accuracy_percentage"] = round(accuracy, 1)
        
        return fan
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting fan profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Active Event ==============

@router.get("/active-event")
async def get_active_event():
    """Get the currently active event for fan scoring"""
    try:
        # Find event marked as active for fan scoring
        event = await db.fan_active_event.find_one({"is_active": True}, {"_id": 0})
        
        if not event:
            # Return default/latest event
            return {
                "has_active_event": False,
                "message": "No active event. Check back during the next live event!"
            }
        
        # Get current fight info
        current_bout = None
        if event.get("current_bout_id"):
            current_bout = await db.bouts.find_one(
                {"bout_id": event["current_bout_id"]},
                {"_id": 0, "bout_id": 1, "fighter1": 1, "fighter2": 1, "currentRound": 1, "totalRounds": 1, "status": 1}
            )
        
        return {
            "has_active_event": True,
            "event_name": event.get("event_name", "Live Event"),
            "event_id": event.get("event_id"),
            "current_bout": current_bout,
            "scoring_open": event.get("scoring_open", False),
            "current_round": event.get("current_round", 1),
            "scoring_deadline": event.get("scoring_deadline")
        }
    except Exception as e:
        logger.error(f"Error getting active event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/set-active-event")
async def set_active_event(event_name: str, event_id: str):
    """Supervisor: Set the active event for fan scoring"""
    try:
        # Deactivate any existing active event
        await db.fan_active_event.update_many({}, {"$set": {"is_active": False}})
        
        # Set new active event
        event_doc = {
            "event_id": event_id,
            "event_name": event_name,
            "is_active": True,
            "current_bout_id": None,
            "current_round": 1,
            "scoring_open": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.fan_active_event.update_one(
            {"event_id": event_id},
            {"$set": event_doc},
            upsert=True
        )
        
        return {"success": True, "message": f"Active event set to: {event_name}"}
    except Exception as e:
        logger.error(f"Error setting active event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/open-scoring")
async def open_scoring_window(bout_id: str, round_number: int, duration_seconds: int = 30):
    """Supervisor: Open scoring window for fans (30 second window after round ends)"""
    try:
        deadline = datetime.now(timezone.utc).timestamp() + duration_seconds
        
        await db.fan_active_event.update_one(
            {"is_active": True},
            {
                "$set": {
                    "current_bout_id": bout_id,
                    "current_round": round_number,
                    "scoring_open": True,
                    "scoring_deadline": deadline,
                    "scoring_opened_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        return {
            "success": True,
            "message": f"Scoring open for Round {round_number}",
            "deadline": deadline,
            "duration_seconds": duration_seconds
        }
    except Exception as e:
        logger.error(f"Error opening scoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/close-scoring")
async def close_scoring_window():
    """Supervisor: Close scoring window"""
    try:
        await db.fan_active_event.update_one(
            {"is_active": True},
            {"$set": {"scoring_open": False, "scoring_deadline": None}}
        )
        
        return {"success": True, "message": "Scoring window closed"}
    except Exception as e:
        logger.error(f"Error closing scoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Score Submission ==============

@router.post("/score/detailed")
async def submit_detailed_score(data: FanScoreSubmission):
    """Submit a detailed score (10-9, 10-8, etc.)"""
    try:
        # Validate scores
        if not (7 <= data.red_score <= 10) or not (7 <= data.blue_score <= 10):
            raise HTTPException(status_code=400, detail="Scores must be between 7 and 10")
        
        # Check if scoring is open
        event = await db.fan_active_event.find_one({"is_active": True})
        if not event or not event.get("scoring_open"):
            raise HTTPException(status_code=400, detail="Scoring is not currently open")
        
        # Check deadline
        if event.get("scoring_deadline") and datetime.now(timezone.utc).timestamp() > event["scoring_deadline"]:
            raise HTTPException(status_code=400, detail="Scoring window has closed")
        
        # Determine winner
        if data.red_score > data.blue_score:
            winner = "RED"
        elif data.blue_score > data.red_score:
            winner = "BLUE"
        else:
            winner = "DRAW"
        
        # Create score document
        score_id = str(uuid.uuid4())[:10]
        score_doc = {
            "score_id": score_id,
            "bout_id": data.bout_id,
            "round_number": data.round_number,
            "red_score": data.red_score,
            "blue_score": data.blue_score,
            "winner": winner,
            "fan_id": data.fan_id,
            "session_id": data.session_id,
            "is_guest": data.fan_id is None,
            "score_type": "detailed",
            "submitted_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Check for duplicate submission
        existing = await db.fan_scores.find_one({
            "bout_id": data.bout_id,
            "round_number": data.round_number,
            "$or": [
                {"fan_id": data.fan_id} if data.fan_id else {"fan_id": None},
                {"session_id": data.session_id} if data.session_id else {"session_id": None}
            ]
        })
        
        if existing:
            # Update existing score
            await db.fan_scores.update_one(
                {"score_id": existing["score_id"]},
                {"$set": score_doc}
            )
            return {"success": True, "message": "Score updated", "score_id": existing["score_id"]}
        
        await db.fan_scores.insert_one(score_doc)
        
        # Update fan stats if registered
        if data.fan_id:
            await db.fan_users.update_one(
                {"fan_id": data.fan_id},
                {"$inc": {"rounds_scored": 1}}
            )
        
        return {
            "success": True,
            "score_id": score_id,
            "message": f"Score submitted: {data.red_score}-{data.blue_score}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting score: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/score/simple")
async def submit_simple_score(data: SimpleScoreSubmission):
    """Submit a simple score (just pick winner)"""
    try:
        if data.winner not in ["RED", "BLUE", "DRAW"]:
            raise HTTPException(status_code=400, detail="Winner must be RED, BLUE, or DRAW")
        
        # Check if scoring is open
        event = await db.fan_active_event.find_one({"is_active": True})
        if not event or not event.get("scoring_open"):
            raise HTTPException(status_code=400, detail="Scoring is not currently open")
        
        # Check deadline
        if event.get("scoring_deadline") and datetime.now(timezone.utc).timestamp() > event["scoring_deadline"]:
            raise HTTPException(status_code=400, detail="Scoring window has closed")
        
        # Convert simple to score
        if data.winner == "RED":
            red_score, blue_score = 10, 9
        elif data.winner == "BLUE":
            red_score, blue_score = 9, 10
        else:
            red_score, blue_score = 10, 10
        
        score_id = str(uuid.uuid4())[:10]
        score_doc = {
            "score_id": score_id,
            "bout_id": data.bout_id,
            "round_number": data.round_number,
            "red_score": red_score,
            "blue_score": blue_score,
            "winner": data.winner,
            "fan_id": data.fan_id,
            "session_id": data.session_id,
            "is_guest": data.fan_id is None,
            "score_type": "simple",
            "submitted_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Check for duplicate
        existing = await db.fan_scores.find_one({
            "bout_id": data.bout_id,
            "round_number": data.round_number,
            "$or": [
                {"fan_id": data.fan_id} if data.fan_id else {"fan_id": None},
                {"session_id": data.session_id} if data.session_id else {"session_id": None}
            ]
        })
        
        if existing:
            await db.fan_scores.update_one(
                {"score_id": existing["score_id"]},
                {"$set": score_doc}
            )
            return {"success": True, "message": "Score updated", "score_id": existing["score_id"]}
        
        await db.fan_scores.insert_one(score_doc)
        
        if data.fan_id:
            await db.fan_users.update_one(
                {"fan_id": data.fan_id},
                {"$inc": {"rounds_scored": 1}}
            )
        
        return {
            "success": True,
            "score_id": score_id,
            "message": f"Score submitted: {data.winner}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting simple score: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Leaderboard ==============

@router.get("/leaderboard")
async def get_leaderboard(event_id: Optional[str] = None, limit: int = 50):
    """Get fan leaderboard - ranked by accuracy"""
    try:
        pipeline = [
            {"$match": {"rounds_scored": {"$gt": 0}}},
            {
                "$addFields": {
                    "accuracy": {
                        "$multiply": [
                            {"$divide": ["$correct_predictions", "$rounds_scored"]},
                            100
                        ]
                    }
                }
            },
            {"$sort": {"accuracy": -1, "rounds_scored": -1}},
            {"$limit": limit},
            {
                "$project": {
                    "_id": 0,
                    "fan_id": 1,
                    "display_name": 1,
                    "rounds_scored": 1,
                    "correct_predictions": 1,
                    "accuracy": {"$round": ["$accuracy", 1]}
                }
            }
        ]
        
        leaderboard = await db.fan_users.aggregate(pipeline).to_list(limit)
        
        # Add rank
        for i, fan in enumerate(leaderboard, 1):
            fan["rank"] = i
        
        return {
            "leaderboard": leaderboard,
            "total_fans": await db.fan_users.count_documents({})
        }
    except Exception as e:
        logger.error(f"Error getting leaderboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Scorecard ==============

@router.get("/scorecard/{bout_id}")
async def get_fan_scorecard(bout_id: str, fan_id: Optional[str] = None, session_id: Optional[str] = None):
    """Get fan's scorecard for a fight with comparison to AI"""
    try:
        # Get bout info
        bout = await db.bouts.find_one(
            {"bout_id": bout_id},
            {"_id": 0, "bout_id": 1, "fighter1": 1, "fighter2": 1, "status": 1}
        )
        
        if not bout:
            raise HTTPException(status_code=404, detail="Bout not found")
        
        # Get fan scores
        query = {"bout_id": bout_id}
        if fan_id:
            query["fan_id"] = fan_id
        elif session_id:
            query["session_id"] = session_id
        else:
            raise HTTPException(status_code=400, detail="Must provide fan_id or session_id")
        
        fan_scores = await db.fan_scores.find(query, {"_id": 0}).sort("round_number", 1).to_list(20)
        
        # Get AI/Official scores
        ai_scores = await db.round_results.find(
            {"bout_id": bout_id},
            {"_id": 0, "round_number": 1, "red_points": 1, "blue_points": 1, "winner": 1}
        ).sort("round_number", 1).to_list(20)
        
        # Calculate totals and accuracy
        fan_total_red = sum(s.get("red_score", 0) for s in fan_scores)
        fan_total_blue = sum(s.get("blue_score", 0) for s in fan_scores)
        ai_total_red = sum(s.get("red_points", 0) for s in ai_scores)
        ai_total_blue = sum(s.get("blue_points", 0) for s in ai_scores)
        
        # Calculate match rate
        correct = 0
        for fs in fan_scores:
            ai_round = next((a for a in ai_scores if a["round_number"] == fs["round_number"]), None)
            if ai_round and fs["winner"] == ai_round.get("winner"):
                correct += 1
        
        accuracy = (correct / len(fan_scores) * 100) if fan_scores else 0
        
        return {
            "bout": bout,
            "fan_scores": fan_scores,
            "ai_scores": ai_scores,
            "fan_total": {"red": fan_total_red, "blue": fan_total_blue},
            "ai_total": {"red": ai_total_red, "blue": ai_total_blue},
            "rounds_matched": correct,
            "total_rounds": len(fan_scores),
            "accuracy_percentage": round(accuracy, 1)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting scorecard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scorecard/{bout_id}/compare")
async def compare_all_fan_scores(bout_id: str):
    """Get aggregated fan scores vs AI for a bout"""
    try:
        # Get all fan scores for this bout
        pipeline = [
            {"$match": {"bout_id": bout_id}},
            {"$group": {
                "_id": "$round_number",
                "red_avg": {"$avg": "$red_score"},
                "blue_avg": {"$avg": "$blue_score"},
                "red_votes": {"$sum": {"$cond": [{"$eq": ["$winner", "RED"]}, 1, 0]}},
                "blue_votes": {"$sum": {"$cond": [{"$eq": ["$winner", "BLUE"]}, 1, 0]}},
                "draw_votes": {"$sum": {"$cond": [{"$eq": ["$winner", "DRAW"]}, 1, 0]}},
                "total_votes": {"$sum": 1}
            }},
            {"$sort": {"_id": 1}}
        ]
        
        fan_aggregate = await db.fan_scores.aggregate(pipeline).to_list(20)
        
        # Get AI scores
        ai_scores = await db.round_results.find(
            {"bout_id": bout_id},
            {"_id": 0}
        ).sort("round_number", 1).to_list(20)
        
        # Get bout info
        bout = await db.bouts.find_one({"bout_id": bout_id}, {"_id": 0, "fighter1": 1, "fighter2": 1})
        
        return {
            "bout": bout,
            "fan_consensus": [
                {
                    "round_number": r["_id"],
                    "avg_red_score": round(r["red_avg"], 1),
                    "avg_blue_score": round(r["blue_avg"], 1),
                    "red_votes": r["red_votes"],
                    "blue_votes": r["blue_votes"],
                    "draw_votes": r["draw_votes"],
                    "total_votes": r["total_votes"],
                    "consensus_winner": "RED" if r["red_votes"] > r["blue_votes"] else "BLUE" if r["blue_votes"] > r["red_votes"] else "DRAW"
                }
                for r in fan_aggregate
            ],
            "ai_scores": ai_scores
        }
    except Exception as e:
        logger.error(f"Error comparing scores: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== QR Code Generation ==============

@router.get("/qr-code/{event_id}")
async def generate_qr_code(event_id: str, base_url: str = Query(...)):
    """Generate QR code for fan access"""
    try:
        import qrcode
        import io
        import base64
        
        # Create fan scoring URL
        fan_url = f"{base_url}/fan?event={event_id}"
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(fan_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return {
            "qr_code_base64": img_str,
            "fan_url": fan_url,
            "event_id": event_id
        }
    except Exception as e:
        logger.error(f"Error generating QR code: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============== Update Accuracy After Official Score ==============

@router.post("/update-accuracy/{bout_id}/{round_number}")
async def update_fan_accuracy(bout_id: str, round_number: int):
    """Update fan accuracy scores after official score is posted"""
    try:
        # Get official score
        official = await db.round_results.find_one({
            "bout_id": bout_id,
            "round_number": round_number
        })
        
        if not official:
            raise HTTPException(status_code=404, detail="Official score not found")
        
        official_winner = official.get("winner")
        
        # Get all fan scores for this round
        fan_scores = await db.fan_scores.find({
            "bout_id": bout_id,
            "round_number": round_number
        }).to_list(10000)
        
        # Update each fan's accuracy
        correct_count = 0
        for score in fan_scores:
            is_correct = score.get("winner") == official_winner
            if is_correct:
                correct_count += 1
            
            # Mark score as correct/incorrect
            await db.fan_scores.update_one(
                {"score_id": score["score_id"]},
                {"$set": {"is_correct": is_correct, "official_winner": official_winner}}
            )
            
            # Update fan user stats
            if score.get("fan_id"):
                if is_correct:
                    await db.fan_users.update_one(
                        {"fan_id": score["fan_id"]},
                        {"$inc": {"correct_predictions": 1}}
                    )
        
        return {
            "success": True,
            "total_scores": len(fan_scores),
            "correct_predictions": correct_count,
            "accuracy_rate": round(correct_count / len(fan_scores) * 100, 1) if fan_scores else 0
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating accuracy: {e}")
        raise HTTPException(status_code=500, detail=str(e))
