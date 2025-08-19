# 🚀 Quick Start - Meeting Automation Tool

## ⚡ Super Fast Setup (2 minutes)

### 1. **Setup**
```bash
python setup.py
```

### 2. **Test Everything**
```bash
python quick_test.py
```

### 3. **Try Sample**
```bash
python run.py sample
```

## 🎯 **What It Does**

1. **📝 AI Summary**: Creates smart meeting summaries using OpenAI
2. **📱 WhatsApp**: Sends summary to your group chat 
3. **📋 Trello**: Finds cards mentioned in meetings and adds discussion notes

## 📱 **Your Setup**

✅ **WhatsApp Group**: `120363401025025313@g.us`  
✅ **Trello Board**: `GAaUJnkk`  
✅ **New Tasks List**: `NEW TASKS`  

## 🧪 **Test With Your Own Transcript**

```bash
python run.py process your_meeting_transcript.txt
```

## 📝 **Sample Meeting Format**

Your transcript can mention Trello cards like:
- "Update on the API documentation task"
- "Working on the database optimization card" 
- "Progress on user authentication"

The tool will find these cards and add meeting notes as comments!

## 🔧 **Troubleshooting**

**Problem**: Some API not working  
**Solution**: Run `python quick_test.py` to see which service failed

**Problem**: Trello cards not found  
**Solution**: Make sure card names in your transcript match your actual Trello card titles

**Problem**: WhatsApp not sending  
**Solution**: Check that your Green API instance is active

## 🎉 **That's It!**

Your tool is ready to automatically process meeting transcripts and keep your team in sync! 

---

**Full documentation**: See `README.md`  
**Advanced usage**: `python src/cli.py --help`